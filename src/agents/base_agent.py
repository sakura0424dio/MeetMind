from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import json
import re
from src.core.state import MeetingState
from src.core.llm import LLMClient


class BaseAgent(ABC):
    """所有智能体的抽象基类"""

    def __init__(self, model_name: Optional[str] = None):
        # 每个Agent都可以共享或独立指定模型
        self.llm = LLMClient(model=model_name) if model_name else LLMClient()
        self.agent_name = self.__class__.__name__

    @abstractmethod
    def run(self, state: MeetingState) -> Dict[str, Any]:
        """
        执行智能体的核心逻辑
        :param state: 共享的全局状态
        :return: 更新状态字段的字典（如 {"summary": "..."}）
        """
        pass

    def _safe_json_parse(self, raw_text: str) -> Dict[str, Any]:
        """
        鲁棒的JSON解析器：处理Markdown包裹、前后缀文字
        """
        if not raw_text:
            return {}

        # 1. 尝试提取 ```json ... ``` 中的内容
        match = re.search(r'```json\s*([\s\S]*?)\s*```', raw_text)
        if match:
            raw_text = match.group(1)
        else:
            # 2. 尝试直接匹配第一个 { 和最后一个 }
            match = re.search(r'(\{[\s\S]*\})', raw_text)
            if match:
                raw_text = match.group(1)

        # 3. 尝试替换常见的非法字符（如末尾多余的逗号）
        raw_text = re.sub(r',\s*\}', '}', raw_text)
        raw_text = re.sub(r',\s*\]', ']', raw_text)

        try:
            return json.loads(raw_text)
        except json.JSONDecodeError as e:
            print(f"[{self.agent_name}] JSON解析失败: {e}")
            print(f"原始内容预览: {raw_text[:200]}...")
            return {}

    def _handle_error(self, error_msg: str) -> Dict[str, Any]:
        """统一错误返回格式"""
        print(f"[{self.agent_name}] 错误: {error_msg}")
        return {"error": error_msg, f"{self.agent_name.lower()}_status": "failed"}