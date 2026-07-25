"""SQLite 数据库管理"""

import sqlite3
import os
import json
from datetime import datetime
from typing import Optional
from app.config import settings


class Database:
    def __init__(self):
        os.makedirs(os.path.dirname(settings.db_path), exist_ok=True)
        self.db_path = settings.db_path
        self.init_db()

    def _conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        return conn

    def init_db(self):
        with self._conn() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS knowledge_bases (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    description TEXT DEFAULT '',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    doc_count INTEGER DEFAULT 0,
                    chunk_count INTEGER DEFAULT 0
                );

                CREATE TABLE IF NOT EXISTS documents (
                    id TEXT PRIMARY KEY,
                    kb_id TEXT NOT NULL,
                    filename TEXT NOT NULL,
                    file_type TEXT NOT NULL,
                    file_size INTEGER DEFAULT 0,
                    chunk_count INTEGER DEFAULT 0,
                    status TEXT DEFAULT 'processing',
                    created_at TEXT NOT NULL,
                    error_message TEXT DEFAULT '',
                    FOREIGN KEY (kb_id) REFERENCES knowledge_bases(id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS conversations (
                    id TEXT PRIMARY KEY,
                    kb_ids TEXT DEFAULT '[]',
                    title TEXT DEFAULT '新对话',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    message_count INTEGER DEFAULT 0
                );

                CREATE TABLE IF NOT EXISTS messages (
                    id TEXT PRIMARY KEY,
                    conversation_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    sources TEXT DEFAULT '[]',
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS chat_stats (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date TEXT NOT NULL,
                    total_queries INTEGER DEFAULT 0,
                    avg_sources REAL DEFAULT 0,
                    kb_id TEXT DEFAULT ''
                );
            """)

    # ── 知识库 ──
    def create_kb(self, kb_id: str, name: str, description: str = ""):
        now = datetime.now().isoformat()
        with self._conn() as conn:
            conn.execute(
                "INSERT INTO knowledge_bases (id, name, description, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
                (kb_id, name, description, now, now),
            )

    def get_all_kbs(self) -> list[dict]:
        with self._conn() as conn:
            rows = conn.execute("SELECT * FROM knowledge_bases ORDER BY created_at DESC").fetchall()
            return [dict(r) for r in rows]

    def get_kb(self, kb_id: str) -> Optional[dict]:
        with self._conn() as conn:
            row = conn.execute("SELECT * FROM knowledge_bases WHERE id = ?", (kb_id,)).fetchone()
            return dict(row) if row else None

    def delete_kb(self, kb_id: str):
        with self._conn() as conn:
            conn.execute("DELETE FROM documents WHERE kb_id = ?", (kb_id,))
            conn.execute("DELETE FROM knowledge_bases WHERE id = ?", (kb_id,))

    def update_kb_stats(self, kb_id: str, doc_count: int = None, chunk_count: int = None):
        updates = []
        params = []
        if doc_count is not None:
            updates.append("doc_count = ?")
            params.append(doc_count)
        if chunk_count is not None:
            updates.append("chunk_count = ?")
            params.append(chunk_count)
        if updates:
            updates.append("updated_at = ?")
            params.append(datetime.now().isoformat())
            params.append(kb_id)
            with self._conn() as conn:
                conn.execute(f"UPDATE knowledge_bases SET {', '.join(updates)} WHERE id = ?", params)

    # ── 文档 ──
    def add_document(self, doc_id: str, kb_id: str, filename: str, file_type: str, file_size: int):
        now = datetime.now().isoformat()
        with self._conn() as conn:
            conn.execute(
                "INSERT INTO documents (id, kb_id, filename, file_type, file_size, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                (doc_id, kb_id, filename, file_type, file_size, now),
            )

    def get_documents(self, kb_id: str) -> list[dict]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM documents WHERE kb_id = ? ORDER BY created_at DESC", (kb_id,)
            ).fetchall()
            return [dict(r) for r in rows]

    def update_document(self, doc_id: str, status: str = None, chunk_count: int = None, error_message: str = None):
        updates = []
        params = []
        if status is not None:
            updates.append("status = ?")
            params.append(status)
        if chunk_count is not None:
            updates.append("chunk_count = ?")
            params.append(chunk_count)
        if error_message is not None:
            updates.append("error_message = ?")
            params.append(error_message)
        if updates:
            params.append(doc_id)
            with self._conn() as conn:
                conn.execute(f"UPDATE documents SET {', '.join(updates)} WHERE id = ?", params)

    def delete_document(self, doc_id: str):
        with self._conn() as conn:
            conn.execute("DELETE FROM documents WHERE id = ?", (doc_id,))

    def count_docs(self, kb_id: str) -> int:
        with self._conn() as conn:
            row = conn.execute("SELECT COUNT(*) as cnt FROM documents WHERE kb_id = ?", (kb_id,)).fetchone()
            return row["cnt"] if row else 0

    # ── 对话 ──
    def create_conversation(self, conv_id: str, kb_ids: list[str]):
        now = datetime.now().isoformat()
        with self._conn() as conn:
            conn.execute(
                "INSERT INTO conversations (id, kb_ids, created_at, updated_at) VALUES (?, ?, ?, ?)",
                (conv_id, json.dumps(kb_ids), now, now),
            )

    def get_conversations(self) -> list[dict]:
        with self._conn() as conn:
            rows = conn.execute("SELECT * FROM conversations ORDER BY updated_at DESC").fetchall()
            return [dict(r) for r in rows]

    def get_conversation(self, conv_id: str) -> Optional[dict]:
        with self._conn() as conn:
            row = conn.execute("SELECT * FROM conversations WHERE id = ?", (conv_id,)).fetchone()
            return dict(row) if row else None

    def delete_conversation(self, conv_id: str):
        with self._conn() as conn:
            conn.execute("DELETE FROM conversations WHERE id = ?", (conv_id,))

    def add_message(self, msg_id: str, conv_id: str, role: str, content: str, sources: list[dict] = None):
        now = datetime.now().isoformat()
        with self._conn() as conn:
            conn.execute(
                "INSERT INTO messages (id, conversation_id, role, content, sources, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                (msg_id, conv_id, role, content, json.dumps(sources or [], ensure_ascii=False), now),
            )
            conn.execute(
                "UPDATE conversations SET updated_at = ?, message_count = message_count + 1 WHERE id = ?",
                (now, conv_id),
            )
            # 更新标题（用第一条用户消息）
            if role == "user":
                title = content[:30] + ("..." if len(content) > 30 else "")
                conn.execute("UPDATE conversations SET title = ? WHERE id = ? AND title = '新对话'", (title, conv_id))

    def get_messages(self, conv_id: str) -> list[dict]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM messages WHERE conversation_id = ? ORDER BY created_at ASC", (conv_id,)
            ).fetchall()
            return [dict(r) for r in rows]

    def get_recent_messages(self, conv_id: str, limit: int = 10) -> list[dict]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM messages WHERE conversation_id = ? ORDER BY created_at DESC LIMIT ?",
                (conv_id, limit),
            ).fetchall()
            return list(reversed([dict(r) for r in rows]))

    # ── 统计 ──
    def get_stats(self) -> dict:
        with self._conn() as conn:
            kb_count = conn.execute("SELECT COUNT(*) as cnt FROM knowledge_bases").fetchone()["cnt"]
            doc_count = conn.execute("SELECT COUNT(*) as cnt FROM documents").fetchone()["cnt"]
            conv_count = conn.execute("SELECT COUNT(*) as cnt FROM conversations").fetchone()["cnt"]
            msg_count = conn.execute("SELECT COUNT(*) as cnt FROM messages WHERE role='user'").fetchone()["cnt"]
            chunk_total = conn.execute(
                "SELECT COALESCE(SUM(chunk_count), 0) as cnt FROM documents WHERE status='completed'"
            ).fetchone()["cnt"]
            return {
                "kb_count": kb_count,
                "doc_count": doc_count,
                "conv_count": conv_count,
                "query_count": msg_count,
                "chunk_total": chunk_total,
            }


# 全局单例
db = Database()
