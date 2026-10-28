# src/agents/reporters/decision_review_reporter.py
from src.agents.reporters.base_reporter import BaseReporterAgent


class DecisionReviewReporter(BaseReporterAgent):
    """决策评审类会议：严格记录论据、决议状态与行动项，不做主观发挥。"""

    meeting_type = "decision_review"
    display_name = "决策评审纪要"
    emoji = "⚖️"
    persona = "严谨的决策记录官，只记录事实、论据与最终决议，不做主观发挥"

    focus_points = (
        "决策议题与需要拍板的问题",
        "背景、约束条件与决策标准",
        "各方观点、论据与分歧点",
        "最终决议及其明确状态（已决定 / 未决定 / 待审批）",
        "待审批事项、审批人与行动项",
    )

    style_rules = (
        "只陈述摘要中出现的事实，禁止推测或替与会者补充观点。",
        "必须明确区分“讨论意见”和“最终决议”。",
        "如果本次没有形成决议，必须显式写“本次会议未形成决议”。",
        "行动项必须包含任务、负责人、截止时间、验收标准四要素。",
    )

    markdown_outline = """## 一、决策议题
## 二、背景与约束条件
## 三、各方观点与论据（支持方 / 反对方 / 中立）
## 四、方案对比（表格：方案 / 优点 / 缺点 / 结论）
## 五、最终决议（已决定 / 未决定 / 待审批）
## 六、待审批事项与审批人
## 七、行动项（任务 / 负责人 / 截止时间 / 验收标准）"""

    extra_json_rules = (
        "final_decision 必须明确写出决议状态；若无决议，填“本次会议未形成决议”。",
    )

    temperature = 0.2
