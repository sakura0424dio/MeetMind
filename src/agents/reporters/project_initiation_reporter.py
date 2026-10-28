# src/agents/reporters/project_initiation_reporter.py
from src.agents.reporters.base_reporter import BaseReporterAgent


class ProjectInitiationReporter(BaseReporterAgent):
    """立项启动类会议：判断“做不做、怎么做”，强调目标、里程碑与风险。"""

    meeting_type = "project_initiation"
    display_name = "项目立项报告"
    emoji = "🚀"
    persona = "资深游戏制作人兼立项评审专家，擅长判断项目是否值得投入以及如何落地"

    focus_points = (
        "项目定位、目标用户与市场机会",
        "核心玩法差异化与产品竞争力",
        "可量化的核心目标（上线时间、用户量、收入等）",
        "里程碑拆解、时间节点与交付物",
        "团队分工、预算与资源缺口",
        "风险概率、影响程度与应对预案",
    )

    style_rules = (
        "结论先行：开篇用一句话给出项目定位，再展开论证。",
        "能用量化指标的地方必须量化，不要只写“提升体验”这类空话。",
        "里程碑和风险必须用表格呈现。",
        "未明确的事项标注“待确认”，并集中列入立项结论后的待审批事项。",
    )

    markdown_outline = """## 一、项目概览（一句话定位）
## 二、市场背景与机会
## 三、核心目标与成功指标
## 四、里程碑路线图（表格：阶段 / 时间节点 / 交付物）
## 五、团队分工与资源需求
## 六、风险评估矩阵（表格：风险 / 概率 / 影响 / 应对预案）
## 七、立项结论与待审批事项"""

    extra_json_rules = (
        "milestones 必须按时间先后排序。",
        "risk_assessment 中 probability 只能取 高 / 中 / 低。",
    )

    temperature = 0.3
