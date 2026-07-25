"""RAG 核心服务 - 检索增强生成"""

from openai import AsyncOpenAI

from app.config import settings
from app.services.vector_store import vector_store
from app.services.embedding_service import local_embed
from app.database import db


class RAGService:
    """RAG 检索增强生成引擎"""

    def __init__(self):
        self._client = None

    @property
    def client(self) -> AsyncOpenAI:
        if self._client is None:
            api_key = settings.deepseek_api_key
            if not api_key or api_key == "sk-your-api-key-here":
                raise RuntimeError(
                    "未配置 DeepSeek API Key，请在 .env 文件中设置 DEEPSEEK_API_KEY"
                )
            self._client = AsyncOpenAI(
                api_key=api_key,
                base_url=settings.deepseek_base_url,
            )
        return self._client

    async def embed_text(self, text: str) -> list[float]:
        """获取文本的向量表示（本地离线）"""
        return local_embed.embed_one(text)

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """批量获取向量（本地离线）"""
        return local_embed.embed_batch(texts)

    async def retrieve(self, kb_ids: list[str], query_text: str) -> list[dict]:
        """检索相关文档片段"""
        # 如果没有指定知识库，搜索所有知识库
        if not kb_ids:
            all_kbs = db.get_all_kbs()
            kb_ids = [kb["id"] for kb in all_kbs]

        if not kb_ids:
            return []

        # 本地向量化查询文本
        query_embedding = await self.embed_text(query_text)

        # 在向量库中搜索
        results = vector_store.search(kb_ids, query_embedding, top_k=settings.top_k)

        # 补充知识库名称
        kb_map = {kb["id"]: kb["name"] for kb in db.get_all_kbs()}
        for r in results:
            r["kb_name"] = kb_map.get(r["kb_id"], "未知知识库")

        return results

    def _build_context(self, results: list[dict]) -> tuple[str, list[dict]]:
        """构建上下文文本和来源信息"""
        if not results:
            return "", []

        context_parts = []
        sources = []
        total_tokens = 0

        for i, r in enumerate(results):
            content = r["content"]
            est_tokens = int(len(content) / 1.5)
            if total_tokens + est_tokens > settings.max_context_tokens:
                break

            context_parts.append(f"[{i+1}] 来源: {r['metadata'].get('filename', '未知')} | {r['kb_name']}\n{content}")
            sources.append({
                "content": content[:200],
                "filename": r["metadata"].get("filename", "未知"),
                "kb_name": r["kb_name"],
                "score": round(r["score"], 3),
                "chunk_index": i,
            })
            total_tokens += est_tokens

        return "\n\n---\n\n".join(context_parts), sources

    async def chat(self, query: str, kb_ids: list[str], history: list[dict] = None) -> tuple[str, list[dict]]:
        """执行 RAG 问答"""
        # 1. 检索
        results = await self.retrieve(kb_ids, query)
        context, sources = self._build_context(results)

        # 2. 构建 prompt
        system_prompt = """你是一个专业的企业知识库助手。请根据提供的参考资料回答用户问题。

回答规则：
1. 如果参考资料中有相关信息，请基于参考资料给出准确、详细的回答
2. 在回答末尾用 [1]、[2] 等标注信息来源编号
3. 如果参考资料中没有相关信息，请明确告知用户"当前知识库中未找到相关信息"，并给出可能的建议
4. 保持回答简洁专业，避免冗余"""

        if context:
            user_content = f"参考资料：\n\n{context}\n\n用户问题：{query}"
        else:
            user_content = f"当前没有可用的参考资料。\n\n用户问题：{query}"

        # 3. 构建消息列表
        messages = [{"role": "system", "content": system_prompt}]

        if history:
            for msg in history[-settings.max_history_turns * 2 :]:
                if msg["role"] in ("user", "assistant"):
                    messages.append({"role": msg["role"], "content": msg["content"]})

        messages.append({"role": "user", "content": user_content})

        # 4. 调用大模型
        try:
            response = await self.client.chat.completions.create(
                model=settings.chat_model,
                messages=messages,
                temperature=settings.temperature,
                max_tokens=settings.max_tokens,
            )
            answer = response.choices[0].message.content
        except Exception as e:
            answer = f"抱歉，AI 服务调用失败：{str(e)}"
            sources = []

        return answer, sources


# 全局单例
rag_service = RAGService()
