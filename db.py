# db.py
import sqlite3
import json
from datetime import datetime
from typing import List, Dict, Any, Optional

DB_PATH = "meetings.db"

def get_connection():
    """获取数据库连接，启用外键和字典游标"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """初始化数据库表（如果不存在则创建）"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS meetings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            meeting_type TEXT,
            speaker_count INTEGER,
            message_count INTEGER,
            full_transcript TEXT,
            summary TEXT,
            report_markdown TEXT,
            report_json TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()
    print("✅ 数据库初始化完成 (meetings.db)")

def save_meeting(data: Dict[str, Any]) -> int:
    """
    存储会议记录
    data 应包含: title, meeting_type, speaker_count, message_count,
                full_transcript, summary, report_markdown, report_json
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO meetings (
            title, meeting_type, speaker_count, message_count,
            full_transcript, summary, report_markdown, report_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        data.get('title', '未命名会议'),
        data.get('meeting_type', ''),
        data.get('speaker_count', 0),
        data.get('message_count', 0),
        data.get('full_transcript', ''),
        data.get('summary', ''),
        data.get('report_markdown', ''),
        data.get('report_json', '')
    ))
    conn.commit()
    last_id = cursor.lastrowid
    conn.close()
    return last_id

def get_all_meetings(limit: int = 50) -> List[Dict[str, Any]]:
    """获取所有会议列表（按时间倒序）"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, title, meeting_type, speaker_count, message_count, created_at
        FROM meetings
        ORDER BY created_at DESC
        LIMIT ?
    """, (limit,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def get_meeting_by_id(meeting_id: int) -> Optional[Dict[str, Any]]:
    """根据 ID 获取会议详情"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM meetings WHERE id = ?", (meeting_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

# 初始化数据库（在导入时自动执行）
init_db()