# src/agents/reporters/general_reporter.py
from src.agents.reporters.base_reporter import BaseReporterAgent


class GeneralReporter(BaseReporterAgent):
    """通用兜底会议：无法归入 7 类专项会议时使用，保持中性完整。"""

    meeting_type = "general"
    display_name = "通用会议纪要"
    emoji = "📝"
    description = "无法归入专项类型时的通用会议记录"

    persona = "专业会议秘书，擅长在不臆测的前提下完整记录讨论与结论"

    focus_points = (
        "会议主题与目的",
        "讨论要点和关键信息",
        "形成的决议或共识",
        "行动项、负责人与截止时间",
        "尚未解决的问题",
    )

    style_rules = (
        "中性、完整、简洁，不添加主观评价。",
        "无法判断的信息标注“待确认”，不做推测。",
        "决议与讨论意见分开记录。",
        "行动项用表格呈现。",
    )

    markdown_outline = """## 一、会议主题
## 二、讨论要点
## 三、形成的决议
## 四、行动项（任务 / 负责人 / 截止时间）
## 五、待解决问题
## 六、备注"""

    temperature = 0.4
