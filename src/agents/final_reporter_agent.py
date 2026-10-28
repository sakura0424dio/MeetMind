"""已弃用：报告生成已拆分为 src/agents/reporters/ 下的 8 个专用 Agent。

src/core/graph.py 不再使用本模块，文件仅保留用于兼容旧引用。
"""

import yaml
import os
import json
from src.agents.base_agent import BaseAgent
from src.core.state import MeetingState


class FinalReporterAgent(BaseAgent):
    def __init__(self):
        super().__init__()
        config_path = os.path.join(os.path.dirname(__file__), '../../config/meeting_schemas.yaml')
        with open(config_path, 'r', encoding='utf-8') as f:
            self.schemas = yaml.safe_load(f)
        self.types = self.schemas['meeting_types']

    def run(self, state: MeetingState) -> dict:
        cumulative_summary = state.get("cumulative_summary")
        meeting_type = state.get("meeting_type")

        if not cumulative_summary:
            return self._handle_error("没有累积摘要，无法生成报告")
        if not meeting_type or meeting_type not in self.types:
            return self._handle_error(f"无效的会议类型: {meeting_type}")

        # 获取对应类型的配置
        type_config = self.types[meeting_type]
        output_schema = type_config.get("output_schema", "{}")
        few_shot = type_config.get("few_shot_example", "")

        # --- 1. 生成结构化 JSON 报告（严格遵循 Schema） ---
        prompt_json = f"""
你是一位游戏公司的会议报告专员。请根据以下会议摘要，生成一份结构化的专项报告。

【会议类型】：{meeting_type}（{type_config.get('description', '')}）

【会议累积摘要】：
{cumulative_summary}

【必须遵循的输出格式（JSON Schema）】：
{output_schema}

【Few-shot示例参考】：
{few_shot}

请严格按照上述 JSON Schema 输出，只输出纯JSON对象，不要包含Markdown代码块包裹，不要添加任何额外文字。
"""

        raw_json_output = self.llm.chat([{"role": "user", "content": prompt_json}])
        if raw_json_output is None:
            return self._handle_error("生成结构化报告失败")

        # 使用基类的安全解析器（它能清洗Markdown和尾随逗号）
        parsed_json = self._safe_json_parse(raw_json_output)

        # --- 2. 生成人类可读的 Markdown 版本 ---
        # 注意：把漂亮的Markdown展示和结构化JSON分开
        prompt_md = f"""
请根据以下会议摘要，生成一份面向游戏团队的可读性极强的Markdown会议报告。

【会议类型】：{meeting_type}
【累积摘要】：{cumulative_summary}
【结构化数据参考】：{json.dumps(parsed_json, ensure_ascii=False, indent=2)}

请输出一份结构清晰、标题层级分明的Markdown文档。标题应与会议类型匹配（如“🎮 项目启动报告”、“🏆 表彰大会纪要”）。
"""
        markdown_report = self.llm.chat([{"role": "user", "content": prompt_md}])
        if markdown_report is None:
            markdown_report = "## 会议报告\n\n（生成失败，请查看结构化数据）"

        return {
            "final_report_json": parsed_json,
            "final_report_markdown": markdown_report
        }