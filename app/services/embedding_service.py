"""Embedding 服务 - 基于 DashScope API（通义千问）"""

import httpx

from app.config import settings


class APIEmbedding:
    """
    使用 DashScope（通义千问）API 生成文本向量。
    模型：text-embedding-v3，1024 维，中文语义理解优秀。
    云端调用，服务器无需加载模型，内存占用极低。
    直接 HTTP 调用，不经过 OpenAI 客户端。
    """

    def __init__(self):
        self._client = None

    @property
    def client(self) -> httpx.AsyncClient:
        if self._client is None:
            api_key = settings.embedding_api_key
            if not api_key or api_key == "sk-your-api-key-here":
                raise RuntimeError(
                    "未配置 Embedding API Key，请在 .env 文件中设置 EMBEDDING_API_KEY"
                )
            self._client = httpx.AsyncClient(
                base_url=settings.embedding_base_url,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                timeout=60.0,
            )
        return self._client

    async def embed_one(self, text: str) -> list[float]:
        """单条文本 -> 向量"""
        response = await self.client.post(
            "/embeddings",
            json={
                "model": settings.embedding_model,
                "input": text,
                "dimensions": settings.embedding_dimensions,
            },
        )
        if response.status_code != 200:
            raise RuntimeError(f"Embedding API 错误: {response.status_code} - {response.text}")
        data = response.json()
        return data["data"][0]["embedding"]

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """批量文本 -> 向量列表"""
        if not texts:
            return []

        all_embeddings = []
        # DashScope 每次最多处理 10 条文本，保守设为 5
        batch_size = 5
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            print(f"[Embedding] 处理批次 {i//batch_size + 1}: {len(batch)} 条文本")
            response = await self.client.post(
                "/embeddings",
                json={
                    "model": settings.embedding_model,
                    "input": batch,
                    "dimensions": settings.embedding_dimensions,
                },
            )
            if response.status_code != 200:
                raise RuntimeError(
                    f"Embedding API 错误 (batch {i//batch_size + 1}): "
                    f"{response.status_code} - {response.text[:200]}"
                )
            data = response.json()
            # 按 index 排序确保顺序正确
            batch_data = sorted(data["data"], key=lambda x: x["index"])
            all_embeddings.extend([d["embedding"] for d in batch_data])

        return all_embeddings


# 全局单例
api_embed = APIEmbedding()
