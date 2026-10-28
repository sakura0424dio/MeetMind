# src/core/state.py
# 确认字段是否齐全，v4.0 需要这些

from typing import Annotated, Sequence, Dict, Any, List, Optional
from langchain_core.messages import BaseMessage
from langgraph.graph import add_messages
from typing_extensions import TypedDict


class MeetingState(TypedDict):
    """Multi-Agent 会议分析系统的全局状态"""

    # ----- 输入层 -----
    transcript: Optional[str]  # 完整会议转录文本
    chunks: Optional[List[str]]  # 切分后的文本块列表
    current_index: int  # 当前处理到第几块

    # ----- 增量摘要层 -----
    cumulative_summary: Optional[str]  # 累积摘要（不断更新）

    # ----- 分类层 -----
    meeting_type: Optional[str]  # 会议类型 (project_initiation 等)

    # ----- 报告层 -----
    final_report_markdown: Optional[str]  # Markdown 格式报告
    final_report_json: Optional[Dict[str, Any]]  # JSON 结构化数据

    # ----- 系统字段 -----
    current_chunk: Optional[str]  # 当前处理的块（用于增量 Agent）
    retry_count: Optional[int]  # 重试计数（可选）
    error: Optional[str]  # 错误信息

    retry_count: Optional[int] 