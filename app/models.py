"""Pydantic 数据模型"""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


# ── 知识库 ──
class KBCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, description="知识库名称")
    description: str = Field(default="", max_length=500, description="知识库描述")


class KBResponse(BaseModel):
    id: str
    name: str
    description: str
    doc_count: int
    chunk_count: int
    created_at: str
    updated_at: str


# ── 文档 ──
class DocResponse(BaseModel):
    id: str
    kb_id: str
    filename: str
    file_type: str
    file_size: int
    chunk_count: int
    status: str
    error_message: str
    created_at: str


# ── 聊天 ──
class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=5000)
    conversation_id: Optional[str] = Field(default=None, description="对话ID，为空则创建新对话")
    kb_ids: list[str] = Field(default_factory=list, description="知识库ID列表，为空则搜索所有知识库")


class SourceItem(BaseModel):
    content: str
    filename: str
    kb_name: str
    score: float
    chunk_index: int


class ChatResponse(BaseModel):
    conversation_id: str
    message_id: str
    answer: str
    sources: list[SourceItem]


class MessageItem(BaseModel):
    id: str
    role: str
    content: str
    sources: list[dict]
    created_at: str


class ConversationResponse(BaseModel):
    id: str
    kb_ids: list[str]
    title: str
    message_count: int
    created_at: str
    updated_at: str


# ── 统计 ──
class StatsResponse(BaseModel):
    kb_count: int
    doc_count: int
    conv_count: int
    query_count: int
    chunk_total: int
