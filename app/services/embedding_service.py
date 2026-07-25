"""Embedding 服务 - 基于 DashScope API（通义千问）"""

import httpx
from openai import AsyncOpenAI

from app.config import settings


class APIEmbedding:
    """
    使用 DashScope（通义千问）API 生成文本向量。
    模型：text-embedding-v3，1024 维，中文语义理解优秀。
    云端调用，服务器无需加载模型，内存占用极低。
    """

    def __init__(self):
        self._client = None

    @property
    def client(self) -> AsyncOpenAI:
        if self._client is None:
            api_key = settings.embedding_api_key
            if not api_key or api_key == "sk-your-api-key-here":
                raise RuntimeError(
                    "未配置 Embedding API Key，请在 .env 文件中设置 EMBEDDING_API_KEY"
                )
            self._client = AsyncOpenAI(
                api_key=api_key,
                base_url=settings.embedding_base_url,
                http_client=httpx.AsyncClient(),
            )
        return self._client

    async def embed_one(self, text: str) -> list[float]:
        """单条文本 -> 向量"""
        response = await self.client.embeddings.create(
            model=settings.embedding_model,
            input=text,
            dimensions=settings.embedding_dimensions,
        )
        return response.data[0].embedding

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """批量文本 -> 向量列表"""
        if not texts:
            return []

        all_embeddings = []
        # DashScope 每次最多处理 10 条文本
        batch_size = 10
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            response = await self.client.embeddings.create(
                model=settings.embedding_model,
                input=batch,
                dimensions=settings.embedding_dimensions,
            )
            # 按 index 排序确保顺序正确
            batch_data = sorted(response.data, key=lambda x: x.index)
            all_embeddings.extend([d.embedding for d in batch_data])

        return all_embeddings


# 全局单例
api_embed = APIEmbedding()
