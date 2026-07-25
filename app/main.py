"""RAG 企业知识库 - FastAPI 主应用"""

import os
import sys
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware

# 确保项目根目录在 sys.path 中
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config import settings
from app.routers import knowledge, documents, chat

app = FastAPI(
    title=settings.app_name,
    description="基于 RAG 的企业知识库问答系统",
    version="1.0.0",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(knowledge.router)
app.include_router(documents.router)
app.include_router(chat.router)

# 静态文件 - 前端
frontend_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "frontend")
if os.path.exists(frontend_dir):
    app.mount("/static", StaticFiles(directory=frontend_dir), name="static")


@app.get("/")
async def index():
    """前端首页"""
    index_path = os.path.join(frontend_dir, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"message": "RAG 企业知识库 API 已启动", "docs": "/docs"}


@app.get("/debug/config")
async def debug_config():
    """调试：查看配置加载情况（仅 debug 模式）"""
    if not settings.debug:
        return {"detail": "Debug mode disabled"}
    return {
        "api_key_set": bool(settings.deepseek_api_key),
        "api_key_prefix": settings.deepseek_api_key[:10] + "..." if settings.deepseek_api_key else "EMPTY",
        "env_file": ".env",
        "cwd": os.getcwd(),
        "env_has_key": "DEEPSEEK_API_KEY" in os.environ,
        "chat_model": settings.chat_model,
        "embedding_model": settings.embedding_model,
        "embedding_api_key_set": bool(settings.embedding_api_key),
        "embedding_base_url": settings.embedding_base_url,
    }


@app.on_event("startup")
async def startup():
    """启动时初始化"""
    os.makedirs(settings.data_dir, exist_ok=True)
    os.makedirs(settings.upload_dir, exist_ok=True)
    os.makedirs(settings.chroma_dir, exist_ok=True)
    api_status = f"已配置 ({settings.deepseek_api_key[:10]}...)" if settings.deepseek_api_key else "未配置"
    print(f"\n{'='*50}")
    print(f"  {settings.app_name} 已启动")
    print(f"  API Key: {api_status}")
    print(f"  CWD: {os.getcwd()}")
    print(f"  API 文档: http://{settings.host}:{settings.port}/docs")
    print(f"  前端界面: http://{settings.host}:{settings.port}/")
    embed_status = f"已配置 ({settings.embedding_api_key[:8]}...)" if settings.embedding_api_key else "未配置"
    print(f"  Embedding API: {embed_status}")
    print(f"  Embedding 模型: {settings.embedding_model}")
    print(f"{'='*50}\n")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
    )
