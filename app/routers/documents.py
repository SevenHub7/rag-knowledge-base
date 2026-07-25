"""文档上传与管理 API"""

import os
import uuid
import asyncio
from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks

from app.config import settings
from app.database import db
from app.services.document_parser import DocumentParser
from app.services.text_chunker import TextChunker
from app.services.rag_service import rag_service
from app.services.vector_store import vector_store

router = APIRouter(prefix="/api/documents", tags=["文档"])


async def process_document(doc_id: str, kb_id: str, file_path: str):
    """后台任务：解析文档 → 分块 → 向量化 → 存储"""
    try:
        # 1. 解析文档
        text = await asyncio.get_event_loop().run_in_executor(
            None, DocumentParser.parse, file_path
        )

        if not text.strip():
            db.update_document(doc_id, status="failed", error_message="文档内容为空")
            return

        # 2. 文本分块
        chunks = TextChunker.chunk_text(text)
        if not chunks:
            db.update_document(doc_id, status="failed", error_message="分块后内容为空")
            return

        # 3. 批量向量化（本地离线）
        embeddings = await rag_service.embed_batch(chunks)

        # 4. 构建元数据
        filename = os.path.basename(file_path)
        metadatas = [
            {"doc_id": doc_id, "kb_id": kb_id, "filename": filename, "chunk_index": i}
            for i in range(len(chunks))
        ]

        # 5. 存入向量库
        vector_store.add_chunks(kb_id, chunks, embeddings, metadatas)

        # 6. 更新状态
        db.update_document(doc_id, status="completed", chunk_count=len(chunks))

        # 7. 更新知识库统计
        doc_count = db.count_docs(kb_id)
        chunk_count = vector_store.get_kb_chunk_count(kb_id)
        db.update_kb_stats(kb_id, doc_count=doc_count, chunk_count=chunk_count)

    except Exception as e:
        db.update_document(doc_id, status="failed", error_message=str(e))


@router.post("/upload/{kb_id}")
async def upload_document(
    kb_id: str,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
):
    """上传文档到知识库"""
    kb = db.get_kb(kb_id)
    if not kb:
        raise HTTPException(status_code=404, detail="知识库不存在")

    if not DocumentParser.is_supported(file.filename):
        raise HTTPException(
            status_code=400,
            detail=f"不支持的文件格式，支持: {', '.join(DocumentParser.SUPPORTED_TYPES)}",
        )

    os.makedirs(settings.upload_dir, exist_ok=True)
    doc_id = uuid.uuid4().hex[:12]
    ext = os.path.splitext(file.filename)[1]
    safe_filename = f"{doc_id}{ext}"
    file_path = os.path.join(settings.upload_dir, safe_filename)

    content = await file.read()
    with open(file_path, "wb") as f:
        f.write(content)

    db.add_document(doc_id, kb_id, file.filename, ext, len(content))

    background_tasks.add_task(process_document, doc_id, kb_id, file_path)

    return {"doc_id": doc_id, "filename": file.filename, "status": "processing"}


@router.get("/status/{doc_id}")
async def get_document_status(doc_id: str):
    """查询文档处理状态"""
    with db._conn() as conn:
        row = conn.execute("SELECT * FROM documents WHERE id = ?", (doc_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="文档不存在")
        return dict(row)
