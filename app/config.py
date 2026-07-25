"""应用配置管理"""

import os
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    # DeepSeek API
    deepseek_api_key: str = Field(default="")
    deepseek_base_url: str = Field(default="https://api.deepseek.com")
    chat_model: str = Field(default="deepseek-v4-flash")

    # Embedding API（使用 DashScope 通义千问，OpenAI 兼容接口）
    embedding_api_key: str = Field(default="")
    embedding_base_url: str = Field(default="https://dashscope.aliyuncs.com/compatible-mode/v1")
    embedding_model: str = Field(default="text-embedding-v3")
    embedding_dimensions: int = Field(default=1024)

    # 应用
    app_name: str = Field(default="RAG 企业知识库")
    host: str = Field(default="0.0.0.0")
    port: int = Field(default_factory=lambda: int(os.environ.get("PORT", 8000)))
    debug: bool = Field(default=False)

    # 路径
    data_dir: str = Field(default="data")
    upload_dir: str = Field(default="data/uploads")
    chroma_dir: str = Field(default="data/chroma_db")
    db_path: str = Field(default="data/app.db")

    # RAG 参数
    chunk_size: int = Field(default=500)
    chunk_overlap: int = Field(default=100)
    top_k: int = Field(default=5)
    score_threshold: float = Field(default=0.5)
    max_context_tokens: int = Field(default=6000)

    # 聊天
    max_history_turns: int = Field(default=10)
    temperature: float = Field(default=0.3)
    max_tokens: int = Field(default=2000)

    model_config = {"env_file": ".env"}


settings = Settings()
