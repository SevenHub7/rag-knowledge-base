"""向量存储服务 - Chroma 管理"""

import chromadb
from chromadb.config import Settings as ChromaSettings
from typing import Optional
import os
import hashlib

from app.config import settings


class VectorStore:
    """Chroma 向量数据库管理"""

    def __init__(self):
        os.makedirs(settings.chroma_dir, exist_ok=True)
        self.client = chromadb.PersistentClient(
            path=settings.chroma_dir,
            settings=ChromaSettings(anonymized_telemetry=False),
        )

    def _get_collection(self, kb_id: str):
        """获取或创建知识库对应的 collection"""
        return self.client.get_or_create_collection(
            name=f"kb_{kb_id}",
            metadata={"hnsw:space": "cosine"},
        )

    def add_chunks(
        self,
        kb_id: str,
        chunks: list[str],
        embeddings: list[list[float]],
        metadatas: list[dict],
    ):
        """添加文本块到向量库"""
        collection = self._get_collection(kb_id)
        ids = [self._make_id(kb_id, i, m.get("doc_id", "")) for i, m in enumerate(metadatas)]
        collection.add(
            ids=ids,
            embeddings=embeddings,
            documents=chunks,
            metadatas=metadatas,
        )

    def search(
        self,
        kb_ids: list[str],
        query_embedding: list[float],
        top_k: Optional[int] = None,
    ) -> list[dict]:
        """在指定知识库中搜索相似文本"""
        top_k = top_k or settings.top_k
        results = []

        for kb_id in kb_ids:
            try:
                collection = self._get_collection(kb_id)
                if collection.count() == 0:
                    continue
                res = collection.query(
                    query_embeddings=[query_embedding],
                    n_results=min(top_k, collection.count()),
                    include=["documents", "metadatas", "distances"],
                )
                for i in range(len(res["documents"][0])):
                    results.append({
                        "content": res["documents"][0][i],
                        "metadata": res["metadatas"][0][i],
                        "score": 1 - res["distances"][0][i],  # cosine distance -> similarity
                        "kb_id": kb_id,
                    })
            except Exception:
                continue

        # 按相似度排序，取 top_k
        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:top_k]

    def delete_kb(self, kb_id: str):
        """删除整个知识库的向量数据"""
        try:
            self.client.delete_collection(f"kb_{kb_id}")
        except Exception:
            pass

    def delete_doc_chunks(self, kb_id: str, doc_id: str):
        """删除指定文档的所有向量"""
        try:
            collection = self._get_collection(kb_id)
            collection.delete(where={"doc_id": doc_id})
        except Exception:
            pass

    def get_kb_chunk_count(self, kb_id: str) -> int:
        """获取知识库的总块数"""
        try:
            collection = self._get_collection(kb_id)
            return collection.count()
        except Exception:
            return 0

    @staticmethod
    def _make_id(kb_id: str, index: int, doc_id: str) -> str:
        raw = f"{kb_id}_{doc_id}_{index}"
        return hashlib.md5(raw.encode()).hexdigest()


# 全局单例
vector_store = VectorStore()
