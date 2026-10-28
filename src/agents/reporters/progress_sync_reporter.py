# src/agents/reporters/progress_sync_reporter.py
from src.agents.reporters.base_reporter import BaseReporterAgent


class ProgressSyncReporter(BaseReporterAgent):
    """研发进度类会议：按职能拆分进展，突出阻塞与下周可执行计划。"""

    meeting_type = "progress_sync"
    display_name = "研发进度同步报告"
    emoji = "📊"
    persona = "游戏项目经理（PM / Scrum Master），擅长把会议信息整理成可执行的任务清单"

    focus_points = (
        "程序、美术、策划、测试各职能的进展",
        "里程碑当前状态与排期偏差",
        "阻塞问题、影响范围、责任人与预计解除时间",
        "下周计划、负责人与验收标准",
        "资源调配与跨部门依赖",
        "需要管理层拍板的事项",
    )

    style_rules = (
        "极简、可执行，不写没有信息量的套话。",
        "每条计划必须包含负责人和验收标准；未提及则写“待确认”。",
        "里程碑状态用 🟢 正常 / 🟡 有风险 / 🔴 阻塞 标注。",
        "阻塞问题单独成节，并说明对整体排期的影响。",
    )

    markdown_outline = """## 一、本周进展总览（表格：职能 / 已完成 / 进行中 / 风险）
## 二、关键里程碑状态（🟢 正常 / 🟡 有风险 / 🔴 阻塞）
## 三、阻塞与风险（问题 / 影响 / 责任人 / 预计解除时间）
## 四、下周计划（任务 / 负责人 / 验收标准）
## 五、资源调配与跨部门依赖
## 六、需要管理层决策的事项"""

    temperature = 0.2
