import os
import json
import random
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional

# 模拟数据库/外部API的存储（演示用）
_MOCK_TICKET_DB = []


def save_transcript_to_file(transcript: str, base_dir: str = "data/outputs") -> str:
    """
    工具1：将转写文本保存到本地文件
    """
    os.makedirs(base_dir, exist_ok=True)
    filename = f"transcript_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    filepath = os.path.join(base_dir, filename)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(transcript)
    return filepath


def create_jira_ticket(summary: str, assignee: str, priority: str = "Medium",
                       description: str = "") -> Dict[str, Any]:
    """
    工具2：模拟在Jira中创建任务单（Function Calling常用案例）
    """
    ticket_id = f"PROJ-{random.randint(1000, 9999)}"
    ticket = {
        "ticket_id": ticket_id,
        "summary": summary,
        "assignee": assignee,
        "priority": priority,
        "status": "Open",
        "created_at": datetime.now().isoformat(),
        "description": description
    }
    _MOCK_TICKET_DB.append(ticket)
    print(f"[工具调用] ✅ 已创建Jira工单: {ticket_id} -> {assignee}")
    return ticket


def send_wecom_message(content: str, receiver: str = "Team_Group") -> bool:
    """
    工具3：模拟发送企业微信/飞书/钉钉消息
    """
    print(f"[工具调用] 📨 已发送消息给 {receiver}:")
    print(f"   {content[:100]}...")
    return True


def parse_deadline_to_date(deadline_str: str) -> str:
    """
    工具4：解析自然语言时间（如“下周一”）为标准日期，供后续排期使用
    """
    now = datetime.now()
    text = deadline_str.lower()

    if "今天" in text:
        return now.strftime("%Y-%m-%d")
    if "明天" in text:
        return (now + timedelta(days=1)).strftime("%Y-%m-%d")
    if "后天" in text:
        return (now + timedelta(days=2)).strftime("%Y-%m-%d")
    if "周" in text:
        # 简单获取星期几映射（演示用）
        weekdays = {"一": 0, "二": 1, "三": 2, "四": 3, "五": 4, "六": 5, "日": 6}
        for cn, offset in weekdays.items():
            if cn in text:
                days_ahead = offset - now.weekday()
                if days_ahead <= 0:  # 如果本周已过，跳到下周
                    days_ahead += 7
                target = now + timedelta(days=days_ahead)
                return target.strftime("%Y-%m-%d")
    # 兜底
    return "待定"


def get_current_time() -> str:
    """工具5：获取当前时间（Agent有时需要知道时间上下文）"""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


# 工具注册表（便于Agent查询有哪些工具可用）
TOOL_REGISTRY = {
    "save_transcript": save_transcript_to_file,
    "create_jira_ticket": create_jira_ticket,
    "send_wecom_message": send_wecom_message,
    "parse_deadline": parse_deadline_to_date,
    "get_current_time": get_current_time,
}