
import asyncio
import hashlib
import hmac
import logging
import secrets
import threading
import time
import os
import json
import uuid
from pathlib import Path
from datetime import datetime
from typing import Annotated, List, Optional
from urllib.parse import urlparse

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

import dashscope
from dashscope.audio.asr import Recognition, RecognitionCallback, RecognitionResult

import db                                 # ← 确保导入 db
import src.main as agent                  # ← 确保导入 Agent 入口（我们刚改的）
# ============================================================
# 配置
# ============================================================

BASE_DIR = Path(__file__).parent

# 从环境变量读取 API Key（建议在 .env 中设置）
DASHSCOPE_API_KEY = os.environ.get("DASHSCOPE_API_KEY")
if not DASHSCOPE_API_KEY:
    raise ValueError("请设置环境变量 DASHSCOPE_API_KEY")

dashscope.api_key = DASHSCOPE_API_KEY

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ============================================================
# 访问控制配置（V01）
# ============================================================
MEETMIND_API_TOKEN = os.environ.get("MEETMIND_API_TOKEN")
if not MEETMIND_API_TOKEN:
    MEETMIND_API_TOKEN = secrets.token_urlsafe(32)
    # 写回环境变量，确保 uvicorn --reload 的子进程使用同一个令牌
    os.environ.setdefault("MEETMIND_API_TOKEN", MEETMIND_API_TOKEN)
    logger.warning("=" * 64)
    logger.warning("⚠️  未设置 MEETMIND_API_TOKEN，本次运行已生成临时访问令牌：")
    logger.warning("    %s", MEETMIND_API_TOKEN)
    logger.warning("    前端首次操作时会提示输入该令牌。")
    logger.warning("    生产环境请通过环境变量固定设置，避免每次重启都变化。")
    logger.warning("=" * 64)

# 页面、静态资源与健康检查保持公开；其余接口一律需要 Bearer Token
PUBLIC_PATHS = {"/", "/health"}
PUBLIC_PREFIXES = ("/static/",)

app = FastAPI(title="游戏公司智能会议助手 v4.0 - 阿里云实时ASR")

static_dir = BASE_DIR / "static"
static_dir.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


@app.middleware("http")
async def require_api_token(request: Request, call_next):
    """为所有数据与写接口提供统一认证。"""
    path = request.url.path
    if path in PUBLIC_PATHS or path.startswith(PUBLIC_PREFIXES):
        return await call_next(request)

    supplied = request.headers.get("authorization", "")
    expected = f"Bearer {MEETMIND_API_TOKEN}"
    if not hmac.compare_digest(supplied, expected):
        return JSONResponse({"error": "unauthorized"}, status_code=401)

    return await call_next(request)


# ============================================================
# 请求模型与分析资源上限（V02）
# ============================================================
MAX_TRANSCRIPT_CHARS = int(os.environ.get("MEETMIND_MAX_TRANSCRIPT_CHARS", "100000"))
MAX_CONCURRENT_ANALYSES = int(os.environ.get("MEETMIND_MAX_CONCURRENT_ANALYSES", "2"))
ANALYSIS_TIMEOUT_SECONDS = int(os.environ.get("MEETMIND_ANALYSIS_TIMEOUT", "600"))

# 单进程事件循环内的活跃分析计数；检查与自增之间没有 await，因此无需额外锁
_active_analyses = 0


class MeetingLogItem(BaseModel):
    speaker: str = Field(min_length=1, max_length=50)
    text: str = Field(min_length=1, max_length=4000)


class ReportRequest(BaseModel):
    title: Optional[str] = Field(default=None, max_length=200)
    meeting_log: Annotated[List[MeetingLogItem], Field(min_length=1, max_length=2000)]


# ============================================================
# WebSocket 安全配置（V04）
# ============================================================
WS_TICKET_TTL_SECONDS = int(os.environ.get("MEETMIND_WS_TICKET_TTL", "60"))
MAX_WS_CONNECTIONS = int(os.environ.get("MEETMIND_MAX_WS_CONNECTIONS", "20"))
MAX_WS_FRAME_BYTES = int(os.environ.get("MEETMIND_MAX_WS_FRAME_BYTES", str(64 * 1024)))
WS_IDLE_TIMEOUT_SECONDS = int(os.environ.get("MEETMIND_WS_IDLE_TIMEOUT", "60"))
WS_MAX_SESSION_SECONDS = int(os.environ.get("MEETMIND_WS_MAX_SESSION", str(4 * 3600)))

_active_websockets = 0
_used_ws_tickets: dict[str, float] = {}


def _sign_ws_ticket() -> str:
    """签发短时 WebSocket 票据：有效期 + 随机 nonce + HMAC 签名。"""
    expires_at = int(time.time()) + WS_TICKET_TTL_SECONDS
    nonce = secrets.token_hex(8)
    payload = f"{expires_at}.{nonce}"
    signature = hmac.new(
        MEETMIND_API_TOKEN.encode("utf-8"),
        payload.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return f"{payload}.{signature}"


def _verify_ws_ticket(ticket: str) -> bool:
    """校验票据签名与有效期，并保证一次性使用。"""
    try:
        expires_raw, nonce, signature = ticket.rsplit(".", 2)
        expires_at = int(expires_raw)
    except (AttributeError, ValueError):
        return False

    if expires_at < time.time():
        return False

    payload = f"{expires_raw}.{nonce}"
    expected = hmac.new(
        MEETMIND_API_TOKEN.encode("utf-8"),
        payload.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    if not hmac.compare_digest(signature, expected):
        return False

    if ticket in _used_ws_tickets:
        return False

    # 清理已过期票据，避免内存无界增长
    now = time.time()
    for used_ticket, used_expiry in list(_used_ws_tickets.items()):
        if used_expiry < now:
            del _used_ws_tickets[used_ticket]
    _used_ws_tickets[ticket] = expires_at
    return True


def _origin_allowed(websocket: WebSocket) -> bool:
    """
    WebSocket Origin 校验：
    - 配置了 MEETMIND_ALLOWED_ORIGINS 时使用显式白名单；
    - 否则要求 Origin 与 Host 同源。
    非浏览器客户端可能不发送 Origin，它们仍需通过票据认证。
    """
    origin = websocket.headers.get("origin")
    if not origin:
        return True

    origin = origin.rstrip("/")
    configured = os.environ.get("MEETMIND_ALLOWED_ORIGINS", "")
    if configured:
        allowed = {
            item.strip().rstrip("/")
            for item in configured.split(",")
            if item.strip()
        }
        return origin in allowed

    host = websocket.headers.get("host", "")
    return urlparse(origin).netloc == host


# ============================================================
# 路由
# ============================================================

@app.get("/")
async def get_index():
    html_path = static_dir / "index.html"
    if html_path.exists():
        with open(html_path, "r", encoding="utf-8") as f:
            return HTMLResponse(f.read())
    return HTMLResponse(f"<h1>请创建 {html_path} 文件</h1>")


@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "meeting-assistant-v4-alibaba"}


@app.get("/api/ws_ticket")
async def get_ws_ticket():
    """签发一次性 WebSocket 票据（需 Bearer Token，由 HTTP 中间件校验）。"""
    return {
        "ticket": _sign_ws_ticket(),
        "expires_in": WS_TICKET_TTL_SECONDS,
    }


@app.post("/api/generate_report")
async def generate_report(payload: ReportRequest):
    """
    接收前端发送的会议对话 (meetingLog)
    调用 Multi-Agent 生成报告并存储到数据库

    资源约束：
    - 单条消息 ≤ 4000 字符，最多 2000 条，总字符数 ≤ MAX_TRANSCRIPT_CHARS
    - 同时最多 MAX_CONCURRENT_ANALYSES 个分析任务
    - 单次分析最长 ANALYSIS_TIMEOUT_SECONDS 秒
    """
    global _active_analyses

    total_chars = sum(len(item.text) for item in payload.meeting_log)
    if total_chars > MAX_TRANSCRIPT_CHARS:
        raise HTTPException(
            status_code=413,
            detail=f"会议记录超过上限（{MAX_TRANSCRIPT_CHARS} 字符）",
        )

    if _active_analyses >= MAX_CONCURRENT_ANALYSES:
        raise HTTPException(status_code=429, detail="分析任务繁忙，请稍后重试")

    title = payload.title or f"会议 {datetime.now().strftime('%Y-%m-%d %H:%M')}"

    # 1. 组装纯文本转录（格式：发言人：内容）
    full_transcript = "\n".join(
        f"{item.speaker}：{item.text}" for item in payload.meeting_log
    )

    # 统计信息
    speaker_set = {item.speaker for item in payload.meeting_log}
    speaker_count = len(speaker_set)
    message_count = len(payload.meeting_log)

    # 2. 调用 Multi-Agent 分析引擎（线程池执行，避免阻塞事件循环）
    _active_analyses += 1
    request_id = uuid.uuid4().hex
    try:
        result = await asyncio.wait_for(
            asyncio.to_thread(agent.run_analysis_from_transcript, full_transcript),
            timeout=ANALYSIS_TIMEOUT_SECONDS,
        )
    except asyncio.TimeoutError:
        logger.error("生成报告超时 request_id=%s", request_id)
        return JSONResponse(
            {"error": "分析超时，请缩短会议记录后重试", "request_id": request_id},
            status_code=504,
        )
    except Exception:
        logger.exception("生成报告失败 request_id=%s", request_id)
        return JSONResponse(
            {"error": "报告生成失败，请稍后重试", "request_id": request_id},
            status_code=500,
        )
    finally:
        _active_analyses -= 1

    if result.get("error"):
        return JSONResponse({"error": result["error"]}, status_code=500)

    # 3. 存储到数据库
    db_data = {
        "title": title,
        "meeting_type": result.get("meeting_type", ""),
        "speaker_count": speaker_count,
        "message_count": message_count,
        "full_transcript": full_transcript,
        "summary": result.get("summary", ""),
        "report_markdown": result.get("report_markdown", ""),
        "report_json": json.dumps(result.get("report_json", {}), ensure_ascii=False)
    }
    try:
        meeting_id = db.save_meeting(db_data)
    except Exception:
        logger.exception("保存会议失败 request_id=%s", request_id)
        return JSONResponse(
            {"error": "保存会议失败，请稍后重试", "request_id": request_id},
            status_code=500,
        )

    # 4. 返回结果给前端
    return JSONResponse({
        "success": True,
        "meeting_id": meeting_id,
        "report_markdown": result.get("report_markdown"),
        "report_json": result.get("report_json"),
        "meeting_type": result.get("meeting_type")
    })


@app.get("/api/meetings")
async def get_meetings(limit: int = 50):
    """获取历史会议列表"""
    meetings = db.get_all_meetings(limit)
    return JSONResponse({"meetings": meetings})


@app.get("/api/meetings/{meeting_id}")
async def get_meeting_detail(meeting_id: int):
    """获取特定会议详情"""
    meeting = db.get_meeting_by_id(meeting_id)
    if not meeting:
        raise HTTPException(status_code=404, detail="会议不存在")
    return JSONResponse({"meeting": meeting})
# ============================================================
# 自定义回调类：接收阿里云识别结果并转发给前端
# ============================================================

class AlibabaASRCallback(RecognitionCallback):
    def __init__(self, websocket: WebSocket):
        self.websocket = websocket
        self.loop = asyncio.get_event_loop()
        self.last_sentence_text = ""  # 记录上一次发送的文本，避免重复

    def on_open(self) -> None:
        logger.info("🔗 阿里云ASR WebSocket 连接已打开")

    def on_close(self) -> None:
        logger.info("🔌 阿里云ASR WebSocket 连接已关闭")

    def on_event(self, result: RecognitionResult) -> None:
        """实时识别结果回调"""
        try:
            # 获取句子对象
            sentence = result.get_sentence()
            if sentence is None:
                return

            # ===== 提取文本 =====
            text = None
            if isinstance(sentence, dict):
                text = sentence.get('text', '')
            elif hasattr(sentence, 'get_text'):
                text = sentence.get_text()
            elif hasattr(sentence, 'text'):
                text = sentence.text
            else:
                text = str(sentence)

            # 跳过空文本
            if not text or not text.strip():
                return

            # ===== 检查是否是中间结果 =====
            # 只有句子结束时才发送完整结果
            is_sentence_end = False
            if isinstance(sentence, dict):
                is_sentence_end = sentence.get('sentence_end', False)
            elif hasattr(sentence, 'sentence_end'):
                is_sentence_end = sentence.sentence_end

            # 如果句子还没结束，只记录但不发送（或者只发送最后一次的完整版）
            if not is_sentence_end:
                # 实时中间结果可以存起来，但不发送
                logger.debug(f"⏳ 中间结果: {text}")
                # 如果不想看到中间结果，直接返回
                return

            # 如果文本与上一次相同，不重复发送
            if text == self.last_sentence_text:
                return

            self.last_sentence_text = text

            # ===== 发送最终结果 =====
            logger.info(f"📝 阿里云识别结果: {text}")
            asyncio.run_coroutine_threadsafe(
                self.websocket.send_json({
                    "type": "transcription",
                    "text": text.strip(),
                    "timestamp": time.time()
                }),
                self.loop
            )

        except Exception as e:
            logger.error(f"❌ 处理识别结果时出错: {e}")

    def on_error(self, result) -> None:
        logger.error(f"❌ 阿里云ASR错误: {result}")


# ============================================================
# WebSocket 端点（实时音频流接收）
# ============================================================

@app.websocket("/ws/audio")
async def websocket_audio_endpoint(websocket: WebSocket):
    global _active_websockets

    # 1. Origin 校验，防止跨站 WebSocket 劫持（CSWSH）
    if not _origin_allowed(websocket):
        logger.warning(
            "拒绝 WebSocket 连接：非法 Origin %s",
            websocket.headers.get("origin"),
        )
        await websocket.close(code=1008)
        return

    # 2. 一次性票据认证（浏览器无法为 WebSocket 设置 Authorization 头）
    ticket = websocket.query_params.get("ticket", "")
    if not ticket or not _verify_ws_ticket(ticket):
        logger.warning("拒绝 WebSocket 连接：票据无效、已过期或已使用")
        await websocket.close(code=1008)
        return

    # 3. 并发连接上限
    if _active_websockets >= MAX_WS_CONNECTIONS:
        logger.warning(
            "拒绝 WebSocket 连接：并发连接数达到上限 %s",
            MAX_WS_CONNECTIONS,
        )
        await websocket.close(code=1013)
        return

    await websocket.accept()
    _active_websockets += 1
    session_started_at = time.time()
    client_host = websocket.client.host
    logger.info(f"🔗 WebSocket 连接建立: {client_host}")

    # 用于控制识别线程的停止标志
    stop_flag = threading.Event()
    asr_thread = None
    chunk_count = 0
    byte_count = 0

    try:
        # 创建阿里云ASR识别实例
        callback = AlibabaASRCallback(websocket)
        recognition = Recognition(
            model='qwen-audio-3.0-asr-flash-streaming',
            format='pcm',
            sample_rate=16000,
            callback=callback
        )

        def run_asr():
            """在独立线程中运行阿里云ASR"""
            try:
                recognition.start()
                logger.info("✅ 阿里云ASR 已启动")
                # 持续运行，直到 stop_flag 被设置
                while not stop_flag.is_set():
                    time.sleep(0.1)
                logger.info("🛑 阿里云ASR 停止中...")
            except Exception as e:
                logger.error(f"❌ 阿里云ASR 运行异常: {e}")
            finally:
                recognition.stop()

        # 启动 ASR 线程
        asr_thread = threading.Thread(target=run_asr, daemon=True)
        asr_thread.start()

        while True:
            # 会话总时长上限
            if time.time() - session_started_at > WS_MAX_SESSION_SECONDS:
                logger.info("⏱️ WebSocket 会话达到最大时长，主动关闭")
                break

            # 接收前端发送的 PCM 音频数据；空闲超时防止连接长期占用
            try:
                data = await asyncio.wait_for(
                    websocket.receive_bytes(),
                    timeout=WS_IDLE_TIMEOUT_SECONDS,
                )
            except asyncio.TimeoutError:
                logger.info("⏱️ WebSocket 空闲超时，主动关闭")
                break

            # 单帧大小上限
            if len(data) > MAX_WS_FRAME_BYTES:
                logger.warning(
                    "⚠️ WebSocket 帧过大（%s 字节 > %s 字节），断开连接",
                    len(data),
                    MAX_WS_FRAME_BYTES,
                )
                break

            chunk_count += 1
            byte_count += len(data)

            # 将音频数据送入阿里云ASR
            try:
                recognition.send_audio_frame(data)
            except Exception as e:
                logger.error(f"❌ 发送音频帧失败: {e}")
                break

            # 每 20 个块打印一次调试日志
            if chunk_count % 20 == 0:
                logger.debug(f"📊 已接收 {chunk_count} 个块，{byte_count} 字节")

            # 每 30 个块发送一次统计信息（可选）
            if chunk_count % 30 == 0:
                await websocket.send_json({
                    "type": "stats",
                    "chunks": chunk_count,
                    "bytes": byte_count,
                    "status": "receiving"
                })

    except WebSocketDisconnect:
        logger.info(f"🔌 WebSocket 连接断开: {client_host}，共接收 {chunk_count} 个块，{byte_count} 字节")
    except Exception as e:
        logger.error(f"❌ WebSocket 异常: {e}")
    finally:
        # 设置停止标志，结束 ASR 线程
        stop_flag.set()
        if asr_thread is not None:
            asr_thread.join(timeout=2.0)
        _active_websockets -= 1
        try:
            await websocket.close()
        except Exception:
            pass
        logger.info("✅ 资源清理完成")


# ============================================================
# 启动
# ============================================================

if __name__ == "__main__":
    import uvicorn

    logger.info("=" * 60)
    logger.info("🎙️ 游戏公司智能会议助手 v4.0 - 阿里云实时ASR")
    logger.info("=" * 60)
    logger.info(f"📁 静态文件目录: {static_dir}")
    logger.info(f"🔊 音频格式: PCM 16kHz 单声道 Int16")
    logger.info(f"🤖 ASR 模型: qwen-audio-3.0-asr-flash-streaming")
    logger.info("=" * 60)
    logger.info("🌐 访问地址: http://localhost:8001")
    logger.info("=" * 60)

    uvicorn.run(
        "app:app",
        host="127.0.0.1",   # 仅监听回环地址，外部访问请通过反向代理
        port=8001,
        reload=True,
        log_level="info"
    )