# src/main.py
import re
from src.core.state import MeetingState
from src.core.graph import build_meeting_graph


def chunk_transcript(transcript: str, max_chunk_len: int = 150) -> list:
    """将文本按句子切块"""
    sentences = re.split(r'(?<=[。！？\n])', transcript)
    chunks = []
    current_chunk = ""
    for sent in sentences:
        if not sent.strip():
            continue
        if len(current_chunk) + len(sent) < max_chunk_len:
            current_chunk += sent
        else:
            if current_chunk:
                chunks.append(current_chunk.strip())
            current_chunk = sent
    if current_chunk:
        chunks.append(current_chunk.strip())
    return chunks


def run_analysis_from_transcript(transcript: str):
    """核心分析函数：使用 LangGraph 编排 Multi-Agent 流程"""
    print("🧠 开始 Multi-Agent 分析 (LangGraph)...")

    chunks = chunk_transcript(transcript, max_chunk_len=150)
    print(f"📝 分块完成，共 {len(chunks)} 块")

    state: MeetingState = {
        "transcript": transcript,
        "chunks": chunks,
        "current_index": 0,
        "cumulative_summary": "",
        "meeting_type": None,
        "final_report_markdown": None,
        "final_report_json": None,
        "error": None,
        "retry_count": 0
    }

    graph = build_meeting_graph()
    final_state = graph.invoke(state)

    if final_state.get("error"):
        return {"error": final_state["error"]}

    return {
        "meeting_type": final_state.get("meeting_type"),
        "summary": final_state.get("cumulative_summary"),
        "report_markdown": final_state.get("final_report_markdown"),
        "report_json": final_state.get("final_report_json")
    }