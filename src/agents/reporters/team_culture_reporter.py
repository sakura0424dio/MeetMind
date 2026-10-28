# src/agents/reporters/team_culture_reporter.py
from src.agents.reporters.base_reporter import BaseReporterAgent


class TeamCultureReporter(BaseReporterAgent):
    """团队文化类会议：表彰信息准确，兼顾温度感与战略宣贯。"""

    meeting_type = "team_culture"
    display_name = "团队文化与表彰大会纪要"
    emoji = "🏆"
    persona = "企业文化与 HRBP 负责人，擅长记录表彰、价值观与战略宣导"

    focus_points = (
        "会议主题与整体氛围",
        "奖项、获奖人及获奖事迹",
        "体现公司价值观的行为标杆",
        "战略宣导的核心要点",
        "员工问答（Q&A）与后续跟进",
    )

    style_rules = (
        "语气温暖、正向，但事实必须准确，获奖人姓名不得写错。",
        "表彰信息用表格呈现，奖项与获奖人一一对应。",
        "战略宣导部分用要点式表达，突出“对员工意味着什么”。",
        "Q&A 保留“提问—答复”的对应关系，未答复的问题列入跟进事项。",
    )

    markdown_outline = """## 一、会议主题与氛围
## 二、表彰名单（表格：奖项 / 获奖人 / 获奖事迹）
## 三、价值观与行为标杆
## 四、战略宣贯要点
## 五、员工问答（Q&A）
## 六、后续跟进事项"""

    temperature = 0.6
