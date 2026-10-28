# 🎙️ MeetMind 智能会议助手

一个面向游戏公司的 AI 会议助手：浏览器实时采集麦克风音频 → 阿里云流式 ASR 转写 → LangGraph 多 Agent 分析 → 按会议类型生成 8 种结构完全不同的专业报告，并持久化到 SQLite。

> 当前版本：v4.0（8 个专用报告 Agent 重构版）
> 技术栈：FastAPI + WebSocket + 阿里云 DashScope（ASR / 通义千问）+ LangGraph + SQLite + 原生 HTML/JS

---

## 目录

- [1. 功能概览](#1-功能概览)
- [2. 快速开始](#2-快速开始)
- [3. 使用指南](#3-使用指南)
- [4. 代码结构](#4-代码结构)
- [5. 各模块职责](#5-各模块职责)
- [6. 结构化分析](#6-结构化分析)
- [7. 进阶建议](#7-进阶建议)
- [8. 常见问题排查](#8-常见问题排查)
- [9. 附录](#9-附录)

---

## 1. 功能概览

| 能力 | 说明 |
|---|---|
| 实时录音转写 | 浏览器采集 PCM，经 WebSocket 送入阿里云流式 ASR，逐句返回文本 |
| 手动发言人标注 | 前端提供 6 个发言人按钮，当前选中的发言人会标注到随后识别出的句子上 |
| 增量摘要 | 按 150 字符切块，逐块调用 LLM 更新"累积摘要" |
| 会议类型分类 | 分类 Agent 判断会议属于 7 类专项会议之一，无法判断时归入 `general` |
| 8 种专用报告 | 8 个独立 Agent 分别负责立项、创意、进度、决策、复盘、运营、文化、通用会议 |
| 双格式报告 | 每个 Agent 同时生成结构化 JSON 和人类可读 Markdown |
| 历史留存 | 会议标题、类型、全文转录、摘要、两种报告写入 SQLite |
| 录音下载 | 会议结束后可在浏览器端合成并下载 WAV 文件（用于调试） |
| 命令行测试 | `test_report.py` 支持模拟文本、单文件音频、批量音频测试 |

**业务范围说明**：项目定位为"游戏公司会议"，报告模板中大量使用游戏研发语境（立项、玩法评审、版本排期、活动运营、版本复盘等）。

---

## 2. 快速开始

### 2.1 环境要求

- Python **3.10+**（仓库内 `.venv` 为 3.10.11；代码使用了 `str | None` 等 3.10 语法）
- 可用的阿里云百炼（DashScope）API Key，且已开通流式语音识别与通义千问模型
- 现代浏览器（Chrome / Edge），需要麦克风权限
- 可选：`ffmpeg`（仅在使用 `test_report.py` 的音频转写功能时需要）

### 2.2 安装依赖

```bash
cd D:\aiproject\MeetMind

python -m venv .venv
.venv\Scripts\activate

pip install -r requirements.txt

# requirements.txt 目前遗漏了 PyYAML，需要补装
pip install "pyyaml>=6.0"
```

> ⚠️ 两个依赖注意点：
> 1. 仓库中的 `.venv` 目前几乎是空环境（只有 pip/setuptools/wheel），直接使用前必须安装依赖。
> 2. `requirements.txt` 中的 `whisper` **不是** OpenAI 的 Whisper。若只使用 Web 端实时转写，可以不安装它；若要用 `test_report.py --audio`，请改用：
>    ```bash
>    pip uninstall whisper
>    pip install openai-whisper
>    ```

### 2.3 配置 API Key 与访问令牌

在项目根目录创建 `.env`：

```env
DASHSCOPE_API_KEY=sk-你的百炼APIKey

# 访问令牌：所有数据接口与 WebSocket 都要求携带
MEETMIND_API_TOKEN=请替换为至少32位的随机字符串
```

生成随机令牌的示例：

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

加载机制：`app.py` 导入 `src.main` 时会间接执行 `src/core/llm.py` 中的 `load_dotenv()`，因此 `.env` 会在 `app.py` 读取环境变量之前生效。也可以直接在系统环境变量中设置。

> 如果没有配置 `DASHSCOPE_API_KEY`，`app.py` 启动时会直接抛出：`ValueError: 请设置环境变量 DASHSCOPE_API_KEY`。
>
> 如果没有配置 `MEETMIND_API_TOKEN`，服务会生成一个**临时随机令牌**并打印到启动日志；前端首次操作时需要输入该令牌。生产环境务必显式配置，避免重启后令牌变化。

### 2.4 可选的安全相关环境变量

| 变量 | 默认值 | 说明 |
|---|---|---|
| `MEETMIND_ALLOWED_ORIGINS` | 同源校验 | 逗号分隔的 Origin 白名单，例如 `https://meet.example.com` |
| `MEETMIND_MAX_TRANSCRIPT_CHARS` | `100000` | 单次报告的会议文本总字符上限 |
| `MEETMIND_MAX_CONCURRENT_ANALYSES` | `2` | 同时运行的分析任务数上限 |
| `MEETMIND_ANALYSIS_TIMEOUT` | `600` | 单次分析超时（秒） |
| `MEETMIND_MAX_WS_CONNECTIONS` | `20` | WebSocket 并发连接上限 |
| `MEETMIND_MAX_WS_FRAME_BYTES` | `65536` | 单个音频帧大小上限（字节） |
| `MEETMIND_WS_IDLE_TIMEOUT` | `60` | WebSocket 空闲超时（秒） |
| `MEETMIND_WS_MAX_SESSION` | `14400` | 单次 WebSocket 会话最长时长（秒） |
| `MEETMIND_WS_TICKET_TTL` | `60` | WebSocket 一次性票据有效期（秒） |

### 2.5 启动服务

```bash
python app.py
```

或使用 uvicorn 显式启动（推荐，便于控制 host/端口）：

```bash
uvicorn app:app --host 127.0.0.1 --port 8001 --reload
```

启动后访问：**http://localhost:8001**

默认配置（`app.py` 末尾）：

- host：`127.0.0.1`（仅回环地址；对外提供服务请通过 Nginx/Caddy 反向代理并启用 HTTPS）
- port：`8001`
- `reload=True`（开发模式；生产环境请改为 `False`）
- ASR 模型：`qwen-audio-3.0-asr-flash-streaming`
- 音频格式：PCM、16 kHz、单声道、Int16

> **访问令牌**：页面本身可以公开访问，但点击「开始会议」或「生成报告」时会弹出输入框，需填入 `MEETMIND_API_TOKEN`。令牌只保存在当前标签页的 `sessionStorage` 中，刷新后需要重新输入。

> 麦克风权限限制：浏览器通常只在 **HTTPS** 或 **localhost** 下允许 `getUserMedia`。如果通过局域网 IP（如 `http://192.168.1.10:8001`）访问，麦克风可能无法启用。生产/局域网使用请配置 HTTPS 反向代理。

---

## 3. 使用指南

### 3.1 Web 界面操作流程

1. **选择发言人**：点击顶部"当前发言人"按钮（张伟 / 李婷 / 王磊 / 陈露 / 赵岩 / 刘洋）。
2. **开始会议**：点击「🎤 开始会议」，浏览器请求麦克风权限，前端建立 WebSocket 并开始发送音频。
3. **实时查看转写**：识别结果按句显示在对话框中。ASR 只返回 `sentence_end=True` 的完整句子，中间结果不会展示。
4. **切换发言人**：会议过程中可随时切换，之后识别出的句子归属新的发言人。
5. **结束会议**：点击「⏹ 结束会议」，停止录音并关闭 WebSocket。
6. **生成报告**：点击「📄 生成报告」，前端把所有对话发送到 `POST /api/generate_report`，等待多 Agent 分析完成后在页面下方展示 Markdown 报告。
7. **下载录音**：点击「⬇️ 下载录音」，浏览器把缓存的 Float32 音频做峰值归一化后合成为 16 kHz WAV 下载。

**使用注意**：

- 发言人归属是**手动标注**，不是声纹分离；如果说话人切换时忘记点按钮，记录会归错人。
- `meetingLog` 只保存在页面内存中，刷新页面会丢失本场会议记录（数据库里只有已生成报告的历史）。
- 报告生成是同步阻塞的：会议越长、分块越多，等待时间越长（详见 [6.5 成本与延迟模型](#65-成本与延迟模型)）。
- ASR 文本、LLM 报告与服务端错误均按不可信数据处理：日志与消息列表使用 `textContent`，报告先转义再做受控 Markdown 渲染。

### 3.2 HTTP API

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/` | 返回 `static/index.html` |
| GET | `/health` | 健康检查，返回 `{"status":"ok", ...}` |
| POST | `/api/generate_report` | 提交会议记录，执行分析并落库 |
| GET | `/api/meetings?limit=50` | 获取历史会议列表（不含全文） |
| GET | `/api/meetings/{meeting_id}` | 获取单场会议详情（含全文与报告） |
| WS | `/ws/audio` | 实时音频流与转写结果 |

#### 生成报告

```bash
curl -X POST http://localhost:8001/api/generate_report \
  -H "Content-Type: application/json" \
  -d '{
    "title": "V3.0 版本决策会",
    "meeting_log": [
      {"speaker": "张伟", "text": "今天讨论 V3.0 要不要上公会战。"},
      {"speaker": "李婷", "text": "玩家呼声很高，但研发工期紧张。"},
      {"speaker": "王磊", "text": "最终决定：上公会战，砍掉赠送体力。"}
    ]
  }'
```

响应示例：

```json
{
  "success": true,
  "meeting_id": 12,
  "report_markdown": "# ⚖️ 决策评审纪要：V3.0 版本内容 ...",
  "report_json": {
    "topic": "V3.0 版本内容",
    "arguments": "玩家呼声 vs 研发工期",
    "final_decision": "上公会战，砍掉赠送体力",
    "pending_approvals": [],
    "action_items": [{"task": "更新排期表", "assignee": "研发"}]
  },
  "meeting_type": "decision_review"
}
```

失败时返回 `{"error": "..."}`，HTTP 状态码 500。

#### 查询历史

```bash
# 所有数据接口都需要 Bearer Token
curl -H "Authorization: Bearer $MEETMIND_API_TOKEN" \
     "http://localhost:8001/api/meetings?limit=10"

curl -H "Authorization: Bearer $MEETMIND_API_TOKEN" \
     "http://localhost:8001/api/meetings/12"
```

> 页面、`/health` 与 `/static/*` 保持公开；其余接口未携带正确令牌时返回 `401 {"error": "unauthorized"}`。部署到共享网络前请继续阅读 [7.1 安全](#71-p0安全与可靠性止血)。

### 3.3 WebSocket 协议（`/ws/audio`）

**建立连接前（认证）**

1. 携带 Bearer Token 调用 `GET /api/ws_ticket`，获取一次性票据。
2. 连接 `/ws/audio?ticket=<ticket>`。
3. Origin 必须与请求 Host 同源，或位于 `MEETMIND_ALLOWED_ORIGINS` 白名单中。
4. 票据默认 60 秒有效且只能使用一次；重连时需要重新获取。

```bash
curl -H "Authorization: Bearer $MEETMIND_API_TOKEN" \
     "http://localhost:8001/api/ws_ticket"
```

**客户端 → 服务端**

- 仅发送**二进制帧**：PCM 16 kHz、单声道、16-bit 小端（`Int16Array` 的 buffer）。
- 前端每 4096 个采样点发送一帧。
- 没有开始/停止控制帧；关闭 WebSocket 即结束本次会话。

**服务端 → 客户端**（JSON 文本帧）

```json
{"type": "transcription", "text": "今天我们讨论新版本。", "timestamp": 1710000000.0}
{"type": "stats", "chunks": 30, "bytes": 245760, "status": "receiving"}
```

服务端在连接建立时即启动 ASR；每 30 个音频块发送一次统计信息。

**服务端资源限制**

| 限制 | 默认值 | 环境变量 |
|---|---|---|
| 并发连接数 | 20 | `MEETMIND_MAX_WS_CONNECTIONS` |
| 单帧大小 | 64 KB | `MEETMIND_MAX_WS_FRAME_BYTES` |
| 空闲超时 | 60 秒 | `MEETMIND_WS_IDLE_TIMEOUT` |
| 单会话最长时长 | 4 小时 | `MEETMIND_WS_MAX_SESSION` |
| 票据有效期 | 60 秒 | `MEETMIND_WS_TICKET_TTL` |

超过并发上限返回关闭码 `1013`；Origin 非法、票据无效/过期/重复使用时返回关闭码 `1008`。

### 3.4 命令行测试脚本

`test_report.py` 可以不经过前端直接验证分析链路：

```bash
# 用内置模拟文本测试指定类型
python test_report.py --mock retrospective

# 批量测试全部 7 种内置模拟会议
python test_report.py --all

# 直接提交一段文本
python test_report.py --text "今天我们开个周会，客户端完成 UI 重构……"

# 测试单个音频文件（需要 openai-whisper + ffmpeg）
python test_report.py --audio data/sample_audio/retrospective.wav

# 批量测试文件夹中的音频
python test_report.py --dir data/sample_audio/
```

说明：

- `--mock` 与 `--all` 覆盖 7 种专项类型（不含 `general`）。
- `--audio` / `--dir` 使用 `TranscriptionAgent`（Whisper）先转写，再进入同一套分析流程。
- `--dir` 会尝试从文件名推断预期类型（要求文件名包含类型 key，如 `retrospective`）；`data/sample_audio` 中的文件名不满足该规则，因此多数文件只会做无预期类型测试。

### 3.5 数据库

默认路径：项目工作目录下的 `meetings.db`（`db.py` 使用相对路径 `DB_PATH = "meetings.db"`）。

表 `meetings`：

| 字段 | 类型 | 说明 |
|---|---|---|
| `id` | INTEGER PK AUTOINCREMENT | 会议 ID |
| `title` | TEXT | 会议标题 |
| `meeting_type` | TEXT | 分类结果 |
| `speaker_count` | INTEGER | 发言人数（按 `speaker` 去重） |
| `message_count` | INTEGER | 消息条数 |
| `full_transcript` | TEXT | `发言人：内容` 拼接的完整转录 |
| `summary` | TEXT | 累积摘要 |
| `report_markdown` | TEXT | Markdown 报告 |
| `report_json` | TEXT | JSON 字符串（注意：入库时被 `json.dumps`，查询出来仍是字符串） |
| `created_at` | TIMESTAMP | 默认当前时间 |

`db.init_db()` 在模块导入时自动执行，因此第一次启动就会建表。

---

## 4. 代码结构

```text
MeetMind/
├── app.py                          # FastAPI 入口：HTTP 路由、WebSocket、阿里云实时 ASR
├── db.py                           # SQLite 访问层：建表、保存、查询
├── requirements.txt                # Python 依赖（存在重复项与缺失项，见 §7）
├── README.md                       # 本文档
├── test_report.py                  # 命令行测试：模拟文本 / 音频批量测试
├── meetings.db                     # 运行时生成的 SQLite 数据库
│
├── config/
│   ├── meeting_schemas.yaml        # 8 类会议的描述、JSON Schema、Few-shot 示例
│   └── settings.py                 # 空文件（预留配置入口，当前未被引用）
│
├── data/
│   └── sample_audio/               # 示例音频（用于 Whisper 测试）
│
├── static/
│   └── index.html                  # 单页前端：录音、WebSocket、转写展示、报告渲染
│
└── src/
    ├── main.py                     # 分析流程入口：切块 + 构建状态 + 调用 LangGraph
    ├── core/
    │   ├── state.py                # MeetingState：LangGraph 共享状态类型
    │   ├── llm.py                  # LLMClient：OpenAI 兼容方式调用通义千问
    │   └── graph.py                # 工作流编排：增量摘要 → 分类 → 8 条条件分支
    ├── agents/
    │   ├── base_agent.py           # Agent 抽象基类：LLM 调用、JSON 容错解析、错误格式
    │   ├── incremental_agent.py    # 增量摘要 Agent：逐块更新累积摘要
    │   ├── classifier_agent.py     # 分类 Agent：判断会议类型
    │   ├── final_reporter_agent.py # 【已弃用】旧版统一报告 Agent
    │   ├── transcription_agent.py  # Whisper 转录 Agent（仅测试脚本使用）
    │   └── reporters/
    │       ├── __init__.py         # 导出 8 个报告 Agent
    │       ├── base_reporter.py    # 报告 Agent 基类：JSON + Markdown 两阶段生成
    │       ├── project_initiation_reporter.py   # 🚀 立项启动
    │       ├── creative_design_reporter.py      # 🎨 创意设计
    │       ├── progress_sync_reporter.py        # 📊 研发进度
    │       ├── decision_review_reporter.py      # ⚖️ 决策评审
    │       ├── retrospective_reporter.py        # 🔁 复盘总结
    │       ├── operation_marketing_reporter.py  # 📈 运营市场
    │       ├── team_culture_reporter.py         # 🏆 团队文化
    │       └── general_reporter.py              # 📝 通用兜底
    └── tools/
        └── meeting_tools.py        # 模拟工具集（工单、企业微信、时间解析等），当前未接入主流程
```

---

## 5. 各模块职责

### 5.1 应用与接入层

| 文件 | 核心内容 | 作用 |
|---|---|---|
| `app.py` | `FastAPI` 实例、`/`、`/health`、`/api/*`、`/ws/audio`、`AlibabaASRCallback`、`uvicorn.run` | 系统唯一入口。负责加载 API Key、挂载静态目录、接收前端音频、调用分析引擎、返回报告。 |
| `static/index.html` | 内联 CSS + 原生 JS | 单页 UI。通过 `AudioContext` + `ScriptProcessor` 采集 PCM，`WebSocket` 发送音频，`fetch` 生成报告；包含发言人切换、日志、WAV 下载。 |
| `db.py` | `init_db`、`save_meeting`、`get_all_meetings`、`get_meeting_by_id` | 轻量 SQLite 封装，全部使用参数化 SQL；模块导入即建表。 |

### 5.2 分析与编排层

| 文件 | 核心内容 | 作用 |
|---|---|---|
| `src/main.py` | `chunk_transcript`、`run_analysis_from_transcript` | 把完整转录按中文句末标点切块（默认 150 字符），初始化 `MeetingState`，构建并执行 LangGraph，最终返回类型/摘要/报告。 |
| `src/core/state.py` | `MeetingState(TypedDict)` | 定义所有 Agent 共享的字段：转录、分块、当前索引、累积摘要、会议类型、最终 JSON/Markdown、错误信息。 |
| `src/core/llm.py` | `LLMClient.chat` | 用 `openai` SDK 调用 DashScope 兼容模式（`https://dashscope.aliyuncs.com/compatible-mode/v1`），默认模型 `qwen-plus`。失败时打印并返回 `None`。 |
| `src/core/graph.py` | `REPORTER_CLASSES`、`TYPE_TO_NODE`、`build_meeting_graph` | 编排核心：`incremental → classify → 条件边 → 8 个报告节点之一 → END`。 |

### 5.3 Agent 层

| 文件 | 作用 |
|---|---|
| `src/agents/base_agent.py` | 所有 Agent 的基类：持有 `LLMClient`；提供 `_safe_json_parse`（剥离 Markdown 代码块、修复尾逗号）与 `_handle_error`。 |
| `src/agents/incremental_agent.py` | 串行遍历所有分块，把"旧摘要 + 新发言"交给 LLM，得到更新后的累积摘要。 |
| `src/agents/classifier_agent.py` | 从 YAML 读取类型列表，要求 LLM 只输出类型 key；校验失败时回退为 `general`。 |
| `src/agents/reporters/base_reporter.py` | 报告生成公共逻辑：先按 YAML Schema 生成 JSON，再按子类声明的章节结构生成 Markdown；负责去代码块与失败兜底。 |
| `src/agents/reporters/*_reporter.py` | 8 个专用 Agent。每个类只声明人设、分析重点、写作规则、章节结构、温度与类型标识，由基类复用生成流程。 |
| `src/agents/final_reporter_agent.py` | 已弃用的旧版统一报告 Agent，保留仅用于兼容旧引用。 |
| `src/agents/transcription_agent.py` | 使用 Whisper 做离线音频转写；**不在 Web 主流程中**，仅被 `test_report.py` 使用。 |

### 5.4 配置、工具与测试

| 文件 | 作用 |
|---|---|
| `config/meeting_schemas.yaml` | 8 类会议的单一事实来源：`description`、`output_schema`、`few_shot_example`。报告 Agent 启动时读取并覆盖类属性。 |
| `config/settings.py` | 空文件，当前没有实际作用。 |
| `src/tools/meeting_tools.py` | 模拟工具函数：保存转录、创建 Jira 工单、发送企业微信消息、解析自然语言时间、获取当前时间。提供 `TOOL_REGISTRY`，但**尚未被 Agent 调用**。 |
| `test_report.py` | 测试入口：7 种模拟会议、单音频、批量音频、自定义文本；校验分类结果与关键 JSON 字段。 |
| `requirements.txt` | 依赖清单。存在重复声明（fastapi/uvicorn）、缺少 `pyyaml`、`whisper` 包名有歧义。 |

---

## 6. 结构化分析

### 6.1 分层架构

```text
┌──────────────────────────────────────────────────────────────┐
│  表现层    static/index.html                                  │
│  录音 / 发言人切换 / 实时转写展示 / 报告渲染 / WAV 下载          │
└───────────────┬──────────────────────────────┬───────────────┘
                │ WebSocket(二进制 PCM)         │ HTTP JSON
┌───────────────▼──────────────────────────────▼───────────────┐
│  接入层    app.py (FastAPI)                                   │
│  /ws/audio · /api/generate_report · /api/meetings · /health   │
└───────────────┬──────────────────────────────┬───────────────┘
                │                              │
┌───────────────▼──────────────┐  ┌────────────▼───────────────┐
│  转写层  DashScope 流式 ASR   │  │  编排层  src/core/graph.py  │
│  Recognition + 回调           │  │  LangGraph StateGraph       │
└───────────────┬──────────────┘  └────────────┬───────────────┘
                │ 转录文本                      │
                └──────────────┬───────────────┘
┌──────────────────────────────▼───────────────────────────────┐
│  Agent 层                                                     │
│  IncrementalAgent → ClassifierAgent → 8 × ReporterAgent       │
│  每个 Agent 通过 LLMClient 调用通义千问                        │
└──────────────────────────────┬───────────────────────────────┘
                               │
┌──────────────────────────────▼───────────────────────────────┐
│  持久化层  db.py → SQLite(meetings.db)                        │
└──────────────────────────────────────────────────────────────┘
```

### 6.2 端到端数据流

```text
用户说话
  → 浏览器 AudioContext 采集 Float32 PCM
  → 转 Int16、16kHz、单声道
  → WebSocket 二进制帧
  → app.py 逐帧 recognition.send_audio_frame()
  → DashScope 流式 ASR
  → 回调 on_event() 仅在 sentence_end 时 send_json
  → 前端 addMessage() 追加到 meetingLog
  → 用户点击"生成报告"
  → POST /api/generate_report {meeting_log}
  → 拼接为 "speaker：text" 全文
  → src/main.py chunk_transcript() 按 150 字切块
  → LangGraph:
       incremental → classifier → 条件边 → 对应 Reporter
  → 返回 {meeting_type, summary, report_markdown, report_json}
  → db.save_meeting() 落库
  → 前端渲染 Markdown
```

### 6.3 工作流图

```text
            ┌──────────────┐
            │  incremental │  逐块更新累积摘要
            └──────┬───────┘
                   ▼
            ┌──────────────┐
            │   classify   │  输出 meeting_type
            └──────┬───────┘
                   │ 条件边 TYPE_TO_NODE
     ┌─────────┬───┴───┬─────────┬──────────────┐
     ▼         ▼       ▼         ▼              ▼
  🚀立项    🎨创意   📊进度   ⚖️决策   🔁复盘 / 📈运营 / 🏆文化 / 📝通用
     └─────────┴───┬───┴─────────┴──────────────┘
                   ▼
                  END
```

> 说明：8 个报告节点互斥，依据 `classifier` 的输出只执行其中一个；未知类型默认走 `report_general`。

### 6.4 共享状态

`MeetingState` 是 LangGraph 的全局状态，各节点只返回自己更新的字段：

| 字段 | 写入者 | 用途 |
|---|---|---|
| `transcript` | `src/main.py` | 完整转录 |
| `chunks` | `src/main.py` | 切分后的文本块 |
| `current_index` | 预留 | 当前处理的块索引（增量 Agent 内部实际使用 `enumerate`，未更新该字段） |
| `cumulative_summary` | `IncrementalAgent` | 累积摘要，供分类与报告使用 |
| `meeting_type` | `ClassifierAgent` | 路由依据 |
| `final_report_json` | Reporter | 结构化报告 |
| `final_report_markdown` | Reporter | Markdown 报告 |
| `error` | 各 Agent | 失败信息 |
| `retry_count` | 预留 | 当前未使用（且在 `state.py` 中重复声明） |

### 6.5 成本与延迟模型

设转录文本长度为 `L` 字符，分块大小固定 150 字符：

```text
块数 N ≈ ceil(L / 150)
LLM 调用次数 ≈ N（增量摘要）+ 1（分类）+ 2（每个 Reporter 的 JSON + Markdown）
总调用次数 ≈ N + 3
```

示例估算：

| 会议时长（约） | 转录长度（约） | 分块数 | LLM 调用数 | 体验 |
|---|---|---|---|---|
| 5 分钟 | 1,500 字 | ~10 | ~13 | 可接受 |
| 30 分钟 | 9,000 字 | ~60 | ~63 | 明显等待 |
| 60 分钟 | 18,000 字 | ~120 | ~123 | 分钟级等待，且阻塞事件循环 |

关键结论：

- **调用次数随转录长度线性增长**，且增量摘要是**串行**的；
- `generate_report` 目前是 `async def` 中直接调用同步函数，会阻塞 FastAPI 事件循环；
- `LLMClient` 未设置超时，长文本场景下失败恢复能力较弱；
- 报告阶段只调用 2 次 LLM，相对固定，主要成本来自增量摘要。

### 6.6 Prompt 与 Schema 设计

系统采用"**配置驱动 + 类属性定制**"的混合模式：

1. `config/meeting_schemas.yaml` 提供每类会议的：
   - `description`：给分类器和报告 Agent 的语义说明；
   - `output_schema`：JSON 结构模板；
   - `few_shot_example`：少样本示例。
2. 每个 Reporter 子类提供：
   - `persona`：专业人设；
   - `focus_points`：分析重点；
   - `style_rules`：写作风格；
   - `markdown_outline`：强制章节；
   - `temperature`：生成随机性。
3. `BaseReporterAgent` 负责两阶段生成：
   - 第一阶段：按 Schema 产出 JSON；
   - 第二阶段：把 JSON 作为事实依据，按章节结构产出 Markdown。

这种设计让"新增一种会议类型"只需三步（见 §7.5），也让 8 种报告在结构上有明显区分。

### 6.7 设计优点

- **职责分离清晰**：接入、编排、Agent、持久化边界明确。
- **配置与代码解耦**：Schema 与示例集中在 YAML，便于非开发人员调整。
- **路由显式**：`TYPE_TO_NODE` 与 `REPORTER_CLASSES` 一一对应，新增类型有固定套路。
- **容错意识**：JSON 解析器处理代码块与尾逗号；报告 Markdown 失败时回退为 JSON；分类失败回退 `general`。
- **双格式输出**：JSON 便于下游系统消费，Markdown 便于人阅读。
- **轻量部署**：SQLite + 单进程 FastAPI，无需额外中间件。

### 6.8 当前局限

| 维度 | 问题 |
|---|---|
| 安全 | 已加 Bearer 认证、WS 票据/Origin/连接上限、XSS 转义；仍缺 TLS、按账号限速与 CSP |
| 并发 | 报告分析已移入线程池并限制并发；仍为单进程，无任务队列 |
| 性能 | 增量摘要串行 O(N) 次调用；每请求重建图与多个 LLM 客户端 |
| 可靠性 | LLM 已加超时/重试；SQLite 连接仍未用上下文管理、无 WAL |
| 数据 | 全文与报告明文落库、无留存/删除策略；日志打印会议内容 |
| 质量 | 已有 24 项安全回归测试；仍无业务评测集，JSON Schema 仅靠提示词约束 |
| 功能 | 无自动说话人分离、无实时中间结果、无历史 UI、无报告编辑/导出 |
| 工程 | 依赖未锁定、`requirements.txt` 有重复与缺失、Web 主流程未使用 `src/tools` |
| 前端 | `messageCount` 在开始新会议时未重置；XSS 已修复 |
| 类型 | `MeetingState` 缺少 `audio_path` 字段（`TranscriptionAgent` 使用但未声明）；`retry_count` 重复声明 |
| 部署 | host 已改为 `127.0.0.1`；`reload=True` 且 `/docs` 未关闭 |

---

## 7. 进阶建议

按优先级分为五组。**P0 建议在对外提供服务前完成。**

### 7.1 P0：安全与可靠性止血

1. **加鉴权**：为所有 HTTP 接口与 WebSocket 增加 Bearer Token 或会话认证；`/api/meetings/{id}` 增加归属校验。
2. **WebSocket 加 Origin 白名单**，防止跨站 WebSocket 劫持；限制单 IP 并发连接数。
3. **启用 HTTPS/WSS**：用 Nginx/Caddy 终止 TLS；前端根据 `location.protocol` 选择 `ws://` 或 `wss://`。
4. **修复 XSS**：报告中移除原始 HTML，前端用 `textContent`；若需 Markdown，使用 `marked` + `DOMPurify`。
5. **输入限制**：为 `meeting_log` 定义 Pydantic 模型（元素数、单条长度、总长度上限）；`limit` 增加 `ge/le`。
6. **避免阻塞事件循环**：`await asyncio.to_thread(agent.run_analysis_from_transcript, transcript)`，并加 `asyncio.wait_for` 超时。
7. **LLM 超时与并发控制**：`OpenAI(..., timeout=60, max_retries=2)`；全局信号量限制同时分析任务数。
8. **错误脱敏**：客户端只返回通用错误 + 请求 ID，详细堆栈写服务端日志。
9. **生产配置**：`reload=False`，仅监听内网/回环地址，关闭 `/docs` 与 `/openapi.json`，增加安全响应头与 CSP。

### 7.2 P1：架构与性能

1. **摘要策略升级**：把"逐块串行更新"改为 **Map-Reduce**：
   - Map：并行摘要每个块（受并发上限约束）；
   - Reduce：分段合并摘要，最后再合并一次。
   - 可将 O(N) 串行延迟降为 O(log N) 或 O(N/并发数)。
2. **按 token 切块**：当前按 150 字符硬切，可能割裂语义；建议用 tokenizer 计数并按句子边界聚合。
3. **长会议上限**：设置最大转录长度与最大分块数，超出时拒绝或降级为"仅摘要"。
4. **复用图与客户端**：对 `build_meeting_graph()` 做缓存，8 个 Agent 共享一个 `LLMClient`，减少每请求初始化开销。
5. **异步化**：将 LLM 调用改为 `AsyncOpenAI`，或在独立线程池/任务队列（Celery、RQ、Arq）中执行长任务，接口返回 `task_id`，前端轮询或订阅进度。
6. **流式报告**：利用 LLM 流式输出，边生成边推送到前端，改善长等待体验。

### 7.3 P2：报告质量与评测

1. **结构化校验**：用 Pydantic 模型或 `jsonschema` 校验 `report_json`，失败时自动让模型"修复 JSON"重试一次。
2. **分类评测集**：为 8 类会议各准备 20–50 条真实/合成样本，计算混淆矩阵与准确率；重点关注 `general` 与相邻类型的边界。
3. **报告质量评分**：定义 Rubric（字段完整性、事实一致性、行动项可执行性、格式合规），用 LLM-as-Judge 或人工抽检定期评估。
4. **提示词版本化**：把 `persona`、`focus_points`、`markdown_outline` 纳入版本管理与 A/B 测试，记录每次变更的效果。
5. **事实一致性检查**：对报告中的人名、日期、数字做回查，降低模型幻觉；缺失信息统一写"未提及/待确认"。
6. **回归测试**：用 Mock LLM 对 8 条路由、字段解析、回退逻辑做单元测试（可参考本次重构的验证方式）。

### 7.4 P3：产品能力

1. **自动说话人分离**：接入支持 diarization 的 ASR，去掉手动切换按钮，按声纹自动归属。
2. **实时中间结果**：把 ASR 的 `sentence_end=False` 结果以灰色临时文本展示，提升实时感。
3. **历史会议 UI**：增加会议列表、搜索、详情页、删除/导出；当前后端已有接口，前端未使用。
4. **报告编辑与导出**：支持在线编辑 Markdown，导出 PDF/DOCX，复制为飞书/Notion 文档。
5. **行动项联动**：把 `action_items` 推送到 Jira / 飞书任务 / 企业微信，复用 `src/tools/meeting_tools.py` 并补真实 API。
6. **自定义模板**：允许团队维护自己的会议类型与报告章节（YAML 已经为此打好了基础）。
7. **多语言**：ASR 与报告支持中英混合，适配出海团队。

### 7.5 P4：工程化与可维护性

1. **依赖治理**：
   - 移除重复的 `fastapi` / `uvicorn`；
   - 补充 `pyyaml`；
   - 将 `whisper` 改为 `openai-whisper` 或从主依赖中移除；
   - 使用 `pip-compile` / `uv lock` 生成锁定文件，CI 跑 `pip-audit`。
2. **配置管理**：用 `pydantic-settings` 统一读取 `.env`，替代散落的 `os.getenv`；删除空文件 `config/settings.py` 或真正启用它。
3. **数据库演进**：短期补 `with get_connection()`、WAL、`busy_timeout`；中期迁移到 PostgreSQL 并引入 Alembic。
4. **可观测性**：结构化日志（JSON）、请求 ID、LLM 调用耗时/ token / 费用指标、OpenTelemetry 链路追踪；日志中脱敏转录内容。
5. **自动化**：`pytest` + `ruff` + `mypy` + `pre-commit` + CI；对 8 个 Reporter 做快照测试。
6. **部署**：Dockerfile + 健康检查；生产使用多 worker 或独立任务队列；不要把 `meetings.db` 打进镜像。
7. **新增会议类型的标准流程**：
   1. 在 `config/meeting_schemas.yaml` 增加类型（description / output_schema / few_shot_example）；
   2. 在 `src/agents/reporters/` 新建 Reporter 子类，声明人设、重点、风格、章节、温度；
   3. 在 `reporters/__init__.py` 导出；
   4. 在 `src/core/graph.py` 的 `REPORTER_CLASSES` 与 `TYPE_TO_NODE` 中注册；
   5. 在 `test_report.py` 增加模拟会议与预期字段；
   6. 用 `--mock` 验证路由与字段完整性。

### 7.6 P5：数据与合规

1. **加密与最小化**：数据库加密（SQLCipher 或磁盘加密）；只保留必要字段；提供删除接口与保留期限。
2. **知情同意**：在 UI 明示音频将上传至云端 ASR/LLM，必要时取得参会人同意。
3. **审计**：记录"谁在何时读取了哪场会议"，满足企业内控要求。
4. **数据隔离**：引入用户/租户维度，避免不同团队互相读取会议。

---

## 8. 常见问题排查

| 现象 | 原因 | 处理 |
|---|---|---|
| 启动报 `请设置环境变量 DASHSCOPE_API_KEY` | 未配置 Key | 在 `.env` 或系统环境变量中设置 |
| 启动报 `ModuleNotFoundError: No module named 'yaml'` | 依赖未装全 | `pip install pyyaml` |
| `.venv` 里几乎没有包 | 仓库内虚拟环境未安装依赖 | 激活后 `pip install -r requirements.txt` |
| 麦克风无法启用 | 非 localhost 且非 HTTPS | 用 `http://localhost:8001` 或配置 HTTPS |
| 页面一直"未连接" | 后端未启动 / 端口不对 / 防火墙 | 检查 `http://localhost:8001/health` |
| 没有转写结果 | ASR Key 无权限、音频格式不符、麦克风静音 | 查看后端日志中的 `阿里云ASR错误`；确认 16 kHz PCM |
| 生成报告很慢 | 增量摘要串行调用 LLM | 缩短会议、降低分块数、或按 §7.2 改造 |
| 报告为空 / 字段缺失 | 模型未按 JSON 输出 | 查看 `_safe_json_parse` 日志；加强 Schema 与重试 |
| 分类总是 `general` | 模型输出不在类型列表 | 检查 `meeting_schemas.yaml` 与分类提示词 |
| `test_report.py --audio` 报 Whisper 相关错误 | 安装了错误的 `whisper` 包或缺 ffmpeg | 改用 `openai-whisper` 并安装 ffmpeg |
| 生成报告后页面没有历史记录 | 前端未实现历史列表 UI | 通过 `/api/meetings` 查询，或按 §7.4 扩展 |
| 新会议开始时"生成报告"按钮状态异常 | `messageCount` 未在 `startMeeting` 中重置 | 在开始会议时重置 `messageCount = 0` 并刷新 UI |

---

## 9. 附录

### 9.1 8 种会议类型

| key | 名称 | 适用场景 | 报告核心章节 |
|---|---|---|---|
| `project_initiation` | 🚀 立项启动 | 新项目立项、Kick-off | 市场机会 / 目标 / 里程碑 / 风险矩阵 / 结论 |
| `creative_design` | 🎨 创意设计 | 头脑风暴、玩法/美术评审 | 方案清单 / 方案对比 / 可行性 / 决策 / 修改项 |
| `progress_sync` | 📊 研发进度 | 周会、站会、跨部门协调 | 职能进展 / 里程碑灯 / 阻塞 / 下周计划 |
| `decision_review` | ⚖️ 决策评审 | 版本决策、预算审批、功能裁剪 | 议题 / 观点 / 方案对比 / 决议 / 行动项 |
| `retrospective` | 🔁 复盘总结 | Sprint 复盘、事故复盘 | 时间线 / Keep / Problem / 根因 / SOP |
| `operation_marketing` | 📈 运营市场 | 数据复盘、活动策划、玩家反馈 | 数据快照 / 舆情 / 活动方案 / ROI |
| `team_culture` | 🏆 团队文化 | 表彰评优、全员大会 | 表彰表 / 价值观 / 战略 / Q&A |
| `general` | 📝 通用兜底 | 无法归类的会议 | 主题 / 讨论 / 决议 / 行动项 / 待解决 |

### 9.2 关键环境变量

| 变量 | 必填 | 说明 |
|---|---|---|
| `DASHSCOPE_API_KEY` | 是 | 阿里云百炼 API Key，用于 ASR 与 LLM |
| `MEETMIND_API_TOKEN` | 推荐 | 访问令牌。未设置时启动会生成临时令牌并打印到日志 |
| `MEETMIND_ALLOWED_ORIGINS` | 否 | WebSocket Origin 白名单，逗号分隔；未设置时要求同源 |
| `MEETMIND_MAX_TRANSCRIPT_CHARS` | 否 | 单次报告文本总字符上限，默认 `100000` |
| `MEETMIND_MAX_CONCURRENT_ANALYSES` | 否 | 并发分析任务上限，默认 `2` |
| `MEETMIND_ANALYSIS_TIMEOUT` | 否 | 单次分析超时秒数，默认 `600` |
| `MEETMIND_MAX_WS_CONNECTIONS` | 否 | WebSocket 并发连接上限，默认 `20` |
| `MEETMIND_MAX_WS_FRAME_BYTES` | 否 | 单帧字节上限，默认 `65536` |
| `MEETMIND_WS_IDLE_TIMEOUT` | 否 | WebSocket 空闲超时秒数，默认 `60` |
| `MEETMIND_WS_MAX_SESSION` | 否 | 单次会话最长秒数，默认 `14400` |
| `MEETMIND_WS_TICKET_TTL` | 否 | WS 票据有效期秒数，默认 `60` |

### 9.3 关键端点速查

```text
GET  /                         前端页面（公开）
GET  /health                   健康检查（公开）
GET  /api/ws_ticket            WebSocket 一次性票据（需 Bearer Token）
POST /api/generate_report      生成报告（需 Bearer Token）
GET  /api/meetings?limit=50    会议列表（需 Bearer Token）
GET  /api/meetings/{id}        会议详情（需 Bearer Token）
WS   /ws/audio?ticket=...      实时音频（票据 + Origin 校验）
```

### 9.4 主要模型

| 用途 | 模型 |
|---|---|
| 实时语音识别 | `qwen-audio-3.0-asr-flash-streaming` |
| 摘要 / 分类 / 报告 | `qwen-plus`（DashScope OpenAI 兼容模式） |

---

> 本文档基于当前代码静态整理。若调整了 Agent 结构、配置或部署方式，请同步更新对应章节。
