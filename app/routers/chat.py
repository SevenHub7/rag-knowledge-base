"""聊天 API"""

import json
from fastapi import APIRouter, HTTPException

from app.models import ChatRequest, ChatResponse, SourceItem, ConversationResponse
from app.services.rag_service import rag_service
from app.services.conversation import conversation_service
from app.database import db

router = APIRouter(prefix="/api/chat", tags=["聊天"])


@router.post("/", response_model=ChatResponse)
async def chat(body: ChatRequest):
    """发送消息并获取 AI 回答"""
    # 获取或创建对话
    conv_id = conversation_service.get_or_create_conversation(
        body.conversation_id, body.kb_ids
    )

    # 保存用户消息
    conversation_service.add_user_message(conv_id, body.message)

    # 获取历史消息
    history = conversation_service.get_history(conv_id)

    # 执行 RAG 问答
    answer, sources = await rag_service.chat(body.message, body.kb_ids, history)

    # 保存 AI 回答
    msg_id = conversation_service.add_assistant_message(conv_id, answer, sources)

    return ChatResponse(
        conversation_id=conv_id,
        message_id=msg_id,
        answer=answer,
        sources=[SourceItem(**s) for s in sources],
    )


@router.get("/conversations", response_model=list[ConversationResponse])
async def list_conversations():
    """获取所有对话列表"""
    return conversation_service.list_conversations()


@router.get("/conversations/{conv_id}")
async def get_conversation_messages(conv_id: str):
    """获取对话的所有消息"""
    conv = db.get_conversation(conv_id)
    if not conv:
        raise HTTPException(status_code=404, detail="对话不存在")
    messages = conversation_service.get_messages(conv_id)
    return {
        "conversation": conv,
        "messages": messages,
    }


@router.delete("/conversations/{conv_id}")
async def delete_conversation(conv_id: str):
    """删除对话"""
    conversation_service.delete_conversation(conv_id)
    return {"message": "对话已删除"}


@router.get("/stats")
async def get_stats():
    """获取系统统计"""
    return db.get_stats()
