import yaml
import os
from src.agents.base_agent import BaseAgent
from src.core.state import MeetingState


class ClassifierAgent(BaseAgent):
    def __init__(self):
        super().__init__()
        # 加载YAML配置（只需要读取类型名称和描述）
        config_path = os.path.join(os.path.dirname(__file__), '../../config/meeting_schemas.yaml')
        with open(config_path, 'r', encoding='utf-8') as f:
            self.schemas = yaml.safe_load(f)
        self.types = self.schemas['meeting_types']

    def run(self, state: MeetingState) -> dict:
        cumulative_summary = state.get("cumulative_summary")
        if not cumulative_summary:
            return self._handle_error("没有累积摘要，无法分类")

        # 构造类型列表描述
        type_desc = ""
        for key, conf in self.types.items():
            type_desc += f"- {key}: {conf['description']}\n"

        prompt = f"""
你是一位资深的游戏行业会议分类专家。请根据以下会议摘要，判断本次会议属于哪种类型。

【可选的会议类型】：
{type_desc}

【会议累积摘要】：
{cumulative_summary}

请仔细分析摘要中的讨论焦点、产出物（是决策、创意、进度还是表彰），然后从上述列表中选择**最匹配的唯一一个类型**。

请务必只输出**纯文本类型名称**（例如：project_initiation），不要包含任何其他文字、标点或JSON格式。
"""

        result = self.llm.chat([{"role": "user", "content": prompt}])
        if result is None:
            return self._handle_error("分类失败")

        # 清理可能的多余空格或换行
        meeting_type = result.strip()

        # 验证分类结果是否在YAML定义中
        if meeting_type not in self.types:
            # 兜底：模型输出不在类型列表内时，交给通用报告 Agent，避免误判为某一专项类型
            print(f"[警告] 模型返回未知类型: {meeting_type}，将使用默认类型 'general'")
            meeting_type = "general"

        return {"meeting_type": meeting_type}