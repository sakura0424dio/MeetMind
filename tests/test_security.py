# tests/test_security.py
"""P0 安全修复的回归测试（V01-V04）。

运行方式（项目根目录）：
    python -m unittest discover -s tests -v

说明：
- 使用 FastAPI TestClient，无需启动真实服务或调用阿里云 API。
- 数据库切换到临时目录，不会写入真实 meetings.db。
- ASR 的 Recognition 被替换为假实现，避免联网与计费。
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

# 必须在导入 app 之前设置
os.environ.setdefault("DASHSCOPE_API_KEY", "dummy-test-key")
os.environ["MEETMIND_API_TOKEN"] = "test-token-123"

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient  # noqa: E402
from starlette.websockets import WebSocketDisconnect  # noqa: E402

import app as app_module  # noqa: E402
import db  # noqa: E402

AUTH_HEADERS = {"Authorization": "Bearer test-token-123"}
SAME_ORIGIN = {"origin": "http://testserver"}


class FakeRecognition:
    """避免测试期间连接阿里云 ASR。"""

    def __init__(self, **kwargs):
        pass

    def start(self) -> None:
        pass

    def stop(self) -> None:
        pass

    def send_audio_frame(self, data: bytes) -> None:
        pass


def fake_analysis(transcript: str) -> dict:
    return {
        "meeting_type": "general",
        "summary": "测试摘要",
        "report_markdown": "# 测试报告\n\n内容",
        "report_json": {"ok": True},
    }


class SecurityRegressionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.tmpdir = tempfile.TemporaryDirectory()
        db.DB_PATH = os.path.join(cls.tmpdir.name, "test_meetings.db")
        db.init_db()

        cls.original_runner = app_module.agent.run_analysis_from_transcript
        cls.original_recognition = app_module.Recognition
        app_module.agent.run_analysis_from_transcript = fake_analysis
        app_module.Recognition = FakeRecognition

        cls.client = TestClient(app_module.app)

    @classmethod
    def tearDownClass(cls) -> None:
        app_module.agent.run_analysis_from_transcript = cls.original_runner
        app_module.Recognition = cls.original_recognition
        cls.tmpdir.cleanup()

    def _ticket(self) -> str:
        response = self.client.get("/api/ws_ticket", headers=AUTH_HEADERS)
        self.assertEqual(response.status_code, 200)
        return response.json()["ticket"]

    # ---------- V01：认证 ----------

    def test_health_is_public(self) -> None:
        self.assertEqual(self.client.get("/health").status_code, 200)

    def test_index_is_public(self) -> None:
        self.assertEqual(self.client.get("/").status_code, 200)

    def test_meetings_requires_auth(self) -> None:
        self.assertEqual(self.client.get("/api/meetings").status_code, 401)

    def test_wrong_token_rejected(self) -> None:
        response = self.client.get(
            "/api/meetings",
            headers={"Authorization": "Bearer wrong-token"},
        )
        self.assertEqual(response.status_code, 401)

    def test_meetings_with_auth(self) -> None:
        response = self.client.get("/api/meetings", headers=AUTH_HEADERS)
        self.assertEqual(response.status_code, 200)
        self.assertIn("meetings", response.json())

    def test_report_requires_auth(self) -> None:
        response = self.client.post(
            "/api/generate_report",
            json={"meeting_log": [{"speaker": "张伟", "text": "你好"}]},
        )
        self.assertEqual(response.status_code, 401)

    def test_ws_ticket_requires_auth(self) -> None:
        self.assertEqual(self.client.get("/api/ws_ticket").status_code, 401)

    # ---------- V02：输入与资源限制 ----------

    def test_empty_meeting_log_rejected(self) -> None:
        response = self.client.post(
            "/api/generate_report",
            headers=AUTH_HEADERS,
            json={"meeting_log": []},
        )
        self.assertEqual(response.status_code, 422)

    def test_missing_text_rejected(self) -> None:
        response = self.client.post(
            "/api/generate_report",
            headers=AUTH_HEADERS,
            json={"meeting_log": [{"speaker": "张伟"}]},
        )
        self.assertEqual(response.status_code, 422)

    def test_single_message_too_long_rejected(self) -> None:
        response = self.client.post(
            "/api/generate_report",
            headers=AUTH_HEADERS,
            json={"meeting_log": [{"speaker": "张伟", "text": "字" * 4001}]},
        )
        self.assertEqual(response.status_code, 422)

    def test_total_transcript_too_long_rejected(self) -> None:
        payload = {
            "meeting_log": [
                {"speaker": "张伟", "text": "字" * 2000}
                for _ in range(60)
            ]
        }
        response = self.client.post(
            "/api/generate_report",
            headers=AUTH_HEADERS,
            json=payload,
        )
        self.assertEqual(response.status_code, 413)

    def test_report_success_and_persisted(self) -> None:
        response = self.client.post(
            "/api/generate_report",
            headers=AUTH_HEADERS,
            json={
                "title": "回归测试会议",
                "meeting_log": [
                    {"speaker": "张伟", "text": "今天讨论立项"},
                    {"speaker": "李婷", "text": "确认目标用户"},
                ],
            },
        )
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertTrue(body["success"])
        self.assertEqual(body["report_markdown"], "# 测试报告\n\n内容")

        saved = db.get_meeting_by_id(body["meeting_id"])
        self.assertIsNotNone(saved)
        self.assertEqual(saved["title"], "回归测试会议")
        self.assertEqual(saved["message_count"], 2)
        self.assertEqual(saved["speaker_count"], 2)

    # ---------- V04：WebSocket ----------

    def test_invalid_origin_rejected(self) -> None:
        ticket = self._ticket()
        with self.assertRaises(WebSocketDisconnect):
            with self.client.websocket_connect(
                f"/ws/audio?ticket={ticket}",
                headers={"origin": "http://evil.example"},
            ):
                pass

    def test_missing_ticket_rejected(self) -> None:
        with self.assertRaises(WebSocketDisconnect):
            with self.client.websocket_connect(
                "/ws/audio",
                headers=SAME_ORIGIN,
            ):
                pass

    def test_invalid_ticket_rejected(self) -> None:
        with self.assertRaises(WebSocketDisconnect):
            with self.client.websocket_connect(
                "/ws/audio?ticket=forged.ticket.value",
                headers=SAME_ORIGIN,
            ):
                pass

    def test_valid_ticket_accepted(self) -> None:
        ticket = self._ticket()
        with self.client.websocket_connect(
            f"/ws/audio?ticket={ticket}",
            headers=SAME_ORIGIN,
        ) as websocket:
            websocket.send_bytes(b"\x00" * 512)

    def test_ticket_is_single_use(self) -> None:
        ticket = self._ticket()
        with self.client.websocket_connect(
            f"/ws/audio?ticket={ticket}",
            headers=SAME_ORIGIN,
        ) as websocket:
            websocket.send_bytes(b"\x00" * 512)

        with self.assertRaises(WebSocketDisconnect):
            with self.client.websocket_connect(
                f"/ws/audio?ticket={ticket}",
                headers=SAME_ORIGIN,
            ):
                pass

    def test_oversized_frame_rejected(self) -> None:
        original_limit = app_module.MAX_WS_FRAME_BYTES
        app_module.MAX_WS_FRAME_BYTES = 1024
        try:
            ticket = self._ticket()
            with self.client.websocket_connect(
                f"/ws/audio?ticket={ticket}",
                headers=SAME_ORIGIN,
            ) as websocket:
                websocket.send_bytes(b"\x00" * 4096)
                with self.assertRaises(WebSocketDisconnect):
                    websocket.receive_bytes()
        finally:
            app_module.MAX_WS_FRAME_BYTES = original_limit

    def test_idle_timeout_closes_connection(self) -> None:
        original_timeout = app_module.WS_IDLE_TIMEOUT_SECONDS
        app_module.WS_IDLE_TIMEOUT_SECONDS = 1
        try:
            ticket = self._ticket()
            import time

            with self.client.websocket_connect(
                f"/ws/audio?ticket={ticket}",
                headers=SAME_ORIGIN,
            ) as websocket:
                time.sleep(1.4)
                with self.assertRaises(WebSocketDisconnect):
                    websocket.receive_bytes()
        finally:
            app_module.WS_IDLE_TIMEOUT_SECONDS = original_timeout


class FrontendSecurityTests(unittest.TestCase):
    """V03：确认前端不再把不可信内容直接交给 innerHTML。"""

    @classmethod
    def setUpClass(cls) -> None:
        cls.html_path = ROOT / "static" / "index.html"
        cls.html = cls.html_path.read_text(encoding="utf-8")

    def test_no_template_literal_innerhtml(self) -> None:
        self.assertNotIn("div.innerHTML = `", self.html)
        self.assertNotIn("msgDiv.innerHTML", self.html)

    def test_report_is_escaped_before_render(self) -> None:
        self.assertIn("escapeHtml(result.report_markdown", self.html)
        self.assertIn("reportContent.innerHTML = html", self.html)

    def test_message_uses_text_content(self) -> None:
        self.assertIn("contentSpan.textContent = text", self.html)
        self.assertIn("speakerSpan.textContent", self.html)

    def test_script_syntax(self) -> None:
        match = re.search(r"<script>(.*?)</script>", self.html, re.S)
        self.assertIsNotNone(match, "未找到内联 script")

        with tempfile.NamedTemporaryFile(
            "w", suffix=".js", delete=False, encoding="utf-8"
        ) as handle:
            handle.write(match.group(1))
            script_path = handle.name

        try:
            result = subprocess.run(
                ["node", "--check", script_path],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
            self.assertEqual(
                result.returncode,
                0,
                f"前端脚本语法错误:\n{result.stderr}",
            )
        finally:
            os.unlink(script_path)

    def test_escape_html_blocks_payload(self) -> None:
        """提取页面中的 escapeHtml 函数，用 Node 验证其输出。"""
        match = re.search(
            r"function escapeHtml\(value\) \{.*?\n        \}",
            self.html,
            re.S,
        )
        self.assertIsNotNone(match, "未找到 escapeHtml 函数")

        script = match.group(0) + """
const payload = '<img src=x onerror=alert(1)>';
const out = escapeHtml(payload);
if (out.includes('<') || out.includes('>')) {
  console.error('escapeHtml failed: ' + out);
  process.exit(1);
}
console.log(out);
"""
        result = subprocess.run(
            ["node", "-e", script],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main(verbosity=2)
