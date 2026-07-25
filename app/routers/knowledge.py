"""知识库管理 API"""

import uuid
from fastapi import APIRouter, HTTPException

from app.models import KBCreate, KBResponse
from app.database import db
from app.services.vector_store import vector_store

router = APIRouter(prefix="/api/knowledge", tags=["知识库"])


@router.get("/", response_model=list[KBResponse])
async def list_knowledge_bases():
    """获取所有知识库"""
    return db.get_all_kbs()


@router.post("/", response_model=KBResponse)
async def create_knowledge_base(body: KBCreate):
    """创建新知识库"""
    kb_id = uuid.uuid4().hex[:12]
    db.create_kb(kb_id, body.name, body.description)
    return db.get_kb(kb_id)


@router.get("/{kb_id}", response_model=KBResponse)
async def get_knowledge_base(kb_id: str):
    """获取知识库详情"""
    kb = db.get_kb(kb_id)
    if not kb:
        raise HTTPException(status_code=404, detail="知识库不存在")
    return kb


@router.delete("/{kb_id}")
async def delete_knowledge_base(kb_id: str):
    """删除知识库（同时删除向量数据和文档）"""
    kb = db.get_kb(kb_id)
    if not kb:
        raise HTTPException(status_code=404, detail="知识库不存在")

    # 删除向量数据
    vector_store.delete_kb(kb_id)

    # 删除数据库记录
    db.delete_kb(kb_id)

    return {"message": f"知识库 '{kb['name']}' 已删除"}


@router.get("/{kb_id}/documents")
async def list_documents(kb_id: str):
    """获取知识库下的文档列表"""
    kb = db.get_kb(kb_id)
    if not kb:
        raise HTTPException(status_code=404, detail="知识库不存在")
    return db.get_documents(kb_id)


@router.delete("/{kb_id}/documents/{doc_id}")
async def delete_document(kb_id: str, doc_id: str):
    """删除知识库中的文档"""
    # 删除向量数据
    vector_store.delete_doc_chunks(kb_id, doc_id)

    # 删除数据库记录
    db.delete_document(doc_id)

    # 更新知识库统计
    doc_count = db.count_docs(kb_id)
    chunk_count = vector_store.get_kb_chunk_count(kb_id)
    db.update_kb_stats(kb_id, doc_count=doc_count, chunk_count=chunk_count)

    return {"message": "文档已删除"}
