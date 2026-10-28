import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

class LLMClient:
    def __init__(self, model: str = "qwen-plus"):
        self.client = OpenAI(
            api_key=os.getenv("DASHSCOPE_API_KEY"),
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",  # 百炼兼容模式地址[reference:15]
            timeout=60.0,   # 单次调用超时，避免无限挂起
            max_retries=2,  # 仅对连接失败/5xx 等可重试错误自动重试
        )
        self.model = model

    def chat(self, messages: list, temperature: float = 0.7):
        """同步调用大模型"""
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature
            )
            return response.choices[0].message.content
        except Exception as e:
            print(f"LLM调用失败: {e}")
            return None