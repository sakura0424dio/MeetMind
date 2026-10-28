import os
import whisper
from src.agents.base_agent import BaseAgent
from src.core.state import MeetingState


class TranscriptionAgent(BaseAgent):
    def __init__(self, model_size: str = "base"):
        super().__init__()  # 初始化LLM（虽然这里没用，但保持统一）
        self.model = whisper.load_model(model_size)

    def run(self, state: MeetingState) -> dict:
        audio_path = state.get("audio_path")
        if not audio_path:
            return self._handle_error("未提供音频文件路径")

        if not os.path.exists(audio_path):
            return self._handle_error(f"音频文件不存在: {audio_path}")

        try:
            result = self.model.transcribe(audio_path, language="zh")
            transcript = result["text"]
            print(f"[TranscriptionAgent] 转写完成，共 {len(transcript)} 字符")
            return {"transcript": transcript}
        except Exception as e:
            return self._handle_error(f"转写失败: {str(e)}")