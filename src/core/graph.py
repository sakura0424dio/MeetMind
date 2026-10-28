# src/core/graph.py
from typing import Callable, Literal

from langgraph.graph import StateGraph, END

from src.core.state import MeetingState
from src.agents.incremental_agent import IncrementalAgent
from src.agents.classifier_agent import ClassifierAgent
from src.agents.reporters import (
    CreativeDesignReporter,
    DecisionReviewReporter,
    GeneralReporter,
    OperationMarketingReporter,
    ProgressSyncReporter,
    ProjectInitiationReporter,
    RetrospectiveReporter,
    TeamCultureReporter,
)

# 节点名 -> 专用报告 Agent 类
# 每个节点只负责一种会议类型，由 classify 之后的条件边决定走哪一条路径。
REPORTER_CLASSES = {
    "report_initiation": ProjectInitiationReporter,
    "report_creative": CreativeDesignReporter,
    "report_progress": ProgressSyncReporter,
    "report_decision": DecisionReviewReporter,
    "report_retrospective": RetrospectiveReporter,
    "report_operation": OperationMarketingReporter,
    "report_team_culture": TeamCultureReporter,
    "report_general": GeneralReporter,
}

# 会议类型 -> 报告节点
TYPE_TO_NODE = {
    "project_initiation": "report_initiation",
    "creative_design": "report_creative",
    "progress_sync": "report_progress",
    "decision_review": "report_decision",
    "retrospective": "report_retrospective",
    "operation_marketing": "report_operation",
    "team_culture": "report_team_culture",
    "general": "report_general",
}


def build_meeting_graph():
    """构建带条件分支的会议分析工作流。"""

    workflow = StateGraph(MeetingState)

    incremental_agent = IncrementalAgent()
    classifier_agent = ClassifierAgent()

    def node_incremental(state: MeetingState) -> dict:
        """增量摘要节点：内部循环处理所有分块"""
        return incremental_agent.run(state)

    def node_classify(state: MeetingState) -> dict:
        """分类节点：判断会议类型"""
        return classifier_agent.run(state)

    def make_report_node(agent) -> Callable[[MeetingState], dict]:
        """为一个专用报告 Agent 生成对应的图节点。"""

        def node(state: MeetingState) -> dict:
            return agent.run(state)

        return node

    workflow.add_node("incremental", node_incremental)
    workflow.add_node("classify", node_classify)

    # 8 个专用 Agent，各自独立节点
    for node_name, agent_cls in REPORTER_CLASSES.items():
        workflow.add_node(node_name, make_report_node(agent_cls()))

    # 线性前置流程
    workflow.set_entry_point("incremental")
    workflow.add_edge("incremental", "classify")

    # 条件分支：按分类结果路由到对应的专用 Agent
    def route_to_report(state: MeetingState) -> Literal[
        "report_initiation", "report_creative", "report_progress",
        "report_decision", "report_retrospective", "report_operation",
        "report_team_culture", "report_general"
    ]:
        meeting_type = state.get("meeting_type", "")
        return TYPE_TO_NODE.get(meeting_type, "report_general")

    workflow.add_conditional_edges(
        "classify",
        route_to_report,
        {node_name: node_name for node_name in REPORTER_CLASSES},
    )

    # 所有报告节点汇聚到 END
    for node_name in REPORTER_CLASSES:
        workflow.add_edge(node_name, END)

    return workflow.compile()
