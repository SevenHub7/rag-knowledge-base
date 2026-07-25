"""对话管理服务"""

import uuid
from app.database import db
from app.models import MessageItem


class ConversationService:
    """管理对话历史和上下文"""

    @staticmethod
    def create_conversation(kb_ids: list[str] = None) -> str:
        conv_id = uuid.uuid4().hex[:12]
        db.create_conversation(conv_id, kb_ids or [])
        return conv_id

    @staticmethod
    def get_or_create_conversation(conv_id: str = None, kb_ids: list[str] = None) -> str:
        if conv_id:
            conv = db.get_conversation(conv_id)
            if conv:
                return conv_id
        return ConversationService.create_conversation(kb_ids)

    @staticmethod
    def get_history(conv_id: str) -> list[dict]:
        return db.get_recent_messages(conv_id, limit=settings.max_history_turns * 2)

    @staticmethod
    def add_user_message(conv_id: str, content: str) -> str:
        msg_id = uuid.uuid4().hex[:12]
        db.add_message(msg_id, conv_id, "user", content)
        return msg_id

    @staticmethod
    def add_assistant_message(conv_id: str, content: str, sources: list[dict] = None) -> str:
        msg_id = uuid.uuid4().hex[:12]
        db.add_message(msg_id, conv_id, "assistant", content, sources)
        return msg_id

    @staticmethod
    def list_conversations() -> list[dict]:
        convs = db.get_conversations()
        for c in convs:
            if isinstance(c.get("kb_ids"), str):
                import json
                c["kb_ids"] = json.loads(c["kb_ids"])
        return convs

    @staticmethod
    def get_messages(conv_id: str) -> list[dict]:
        msgs = db.get_messages(conv_id)
        for m in msgs:
            if isinstance(m.get("sources"), str):
                import json
                m["sources"] = json.loads(m["sources"])
        return msgs

    @staticmethod
    def delete_conversation(conv_id: str):
        db.delete_conversation(conv_id)


# 避免循环导入
from app.config import settings
conversation_service = ConversationService()
