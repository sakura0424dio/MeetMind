# src/agents/reporters/retrospective_reporter.py
from src.agents.reporters.base_reporter import BaseReporterAgent


class RetrospectiveReporter(BaseReporterAgent):
    """复盘总结类会议：从现象追到根因，并沉淀可度量的改进措施。"""

    meeting_type = "retrospective"
    display_name = "迭代复盘报告"
    emoji = "🔁"
    persona = "敏捷教练兼复盘引导师，擅长从现象追问根因并沉淀可复用的流程"

    focus_points = (
        "复盘范围、目标与关键事件时间线",
        "做得好的方面（Keep）",
        "做得不好的方面（Problem）",
        "问题根因（人 / 流程 / 工具）",
        "改进措施、负责人、截止时间与度量指标",
        "可沉淀的经验与 SOP",
    )

    style_rules = (
        "对事不对人，描述问题聚焦流程与机制。",
        "每个问题都要追问根因，避免只罗列现象。",
        "改进措施必须可执行、可度量，不能只写“加强沟通”。",
        "用表格呈现“问题 → 根因 → 措施 → 度量指标”的闭环。",
    )

    markdown_outline = """## 一、复盘范围与目标
## 二、事实时间线（关键事件）
## 三、做得好的（Keep）
## 四、做得不好的（Problem）
## 五、根因分析（人 / 流程 / 工具）
## 六、改进措施与 SOP（表格：问题 / 根因 / 措施 / 负责人 / 截止时间 / 度量指标）
## 七、可沉淀的经验"""

    temperature = 0.4
