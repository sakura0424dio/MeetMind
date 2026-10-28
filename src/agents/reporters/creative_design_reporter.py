# src/agents/reporters/creative_design_reporter.py
from src.agents.reporters.base_reporter import BaseReporterAgent


class CreativeDesignReporter(BaseReporterAgent):
    """创意设计类会议：保留发散方案，并收敛出明确决策与修改项。"""

    meeting_type = "creative_design"
    display_name = "创意设计评审纪要"
    emoji = "🎨"
    persona = "游戏创意总监，擅长保留发散想法并把它们收敛成可执行的设计决策"

    focus_points = (
        "讨论议题与创作目标",
        "每个创意方案的核心概念、亮点与代价",
        "方案之间的对比维度（可行性、成本、玩家吸引力、风险）",
        "已确认的决策与仍待验证的假设",
        "具体的修改项、负责人以及后续创意实验",
    )

    style_rules = (
        "保留原始创意的鲜活表达，不要过早否定任何方案。",
        "用“方案 A / 方案 B / 方案 C”命名备选方案，并逐一说明概念、亮点与代价。",
        "严格区分“已决策”与“待验证假设”，后者必须给出验证方式。",
        "修改项写成可执行动作，尽量附上负责人与截止时间。",
    )

    markdown_outline = """## 一、议题与创作目标
## 二、创意方案清单（方案名 / 核心概念 / 亮点 / 风险）
## 三、方案对比（表格：方案 / 可行性 / 成本 / 玩家吸引力 / 结论）
## 四、可行性评估
## 五、最终决策与理由
## 六、修改清单（修改项 / 负责人 / 截止时间）
## 七、下一步创意实验"""

    temperature = 0.8
