# src/agents/incremental_agent.py
from src.agents.base_agent import BaseAgent
from src.core.state import MeetingState

class IncrementalAgent(BaseAgent):
    def __init__(self):
        super().__init__()

    def run(self, state: MeetingState) -> dict:
        # 获取所有分块
        chunks = state.get("chunks", [])
        if not chunks:
            return self._handle_error("没有可用的分块")

        # 获取当前累积摘要（可能已存在）
        cumulative_summary = state.get("cumulative_summary", "")

        print(f"📝 [IncrementalAgent] 开始处理 {len(chunks)} 个分块")

        # 循环处理所有分块
        for idx, chunk in enumerate(chunks):
            if not chunk or not chunk.strip():
                continue

            print(f"  📌 处理第 {idx+1}/{len(chunks)} 块: {chunk[:50]}...")

            prompt = f"""
你是一位游戏公司的会议记录员。你正在实时记录一场会议，需要不断更新"阶段性摘要"。

【之前的会议累积摘要】：
{cumulative_summary if cumulative_summary else "（会议刚开始，暂无历史记录）"}

【最新听到的一段发言】：
{chunk}

请根据这段新发言，**更新**累积摘要。更新后的摘要要包含：
1. 之前已经讨论过的内容（保留）
2. 本次发言带来的新信息、新决策、新待办（追加或修改）
3. 保持摘要连贯、精炼，不要遗漏关键点

请直接输出更新后的完整摘要（不要包含任何额外解释，只输出更新后的摘要文本）：
"""
            new_summary = self.llm.chat([{"role": "user", "content": prompt}])
            if new_summary is None:
                print(f"  ❌ 第 {idx+1} 块处理失败，跳过")
                continue

            cumulative_summary = new_summary
            print(f"  ✅ 第 {idx+1} 块处理完成，当前摘要长度: {len(cumulative_summary)} 字符")

        print(f"✅ [IncrementalAgent] 所有分块处理完成，最终摘要长度: {len(cumulative_summary)} 字符")
        return {"cumulative_summary": cumulative_summary}