from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import time
import logging

from src.smartdocrag.core.config import settings

# 配置日志
logging.basicConfig(
    level=logging.INFO if settings.DEBUG else logging.WARNING,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"{settings.APP_NAME} v{settings.APP_VERSION} 正在启动...")
    # TODO: 后续在这里添加数据库连接、向量索引初始化等

    yield

    logger.info(f"{settings.APP_NAME} 正在关闭...")
    # TODO: 清理资源




# 创建 FastAPI 应用
app = FastAPI(
    title=settings.APP_NAME,
    description="生产级智能文档 RAG 问答系统后端",
    version=settings.APP_VERSION,
    docs_url="/docs" if settings.DEBUG else None,  # 生产环境可关闭 Swagger
    redoc_url="/redoc" if settings.DEBUG else None,
    lifespan=lifespan,
)

# 配置 CORS（允许前端调用，生产时建议限制具体域名）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 开发阶段用 *，生产时改成具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# 中间件：请求耗时日志
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    logger.info(f"{request.method} {request.url.path} - {process_time:.4f}s")
    return response


# ==================== RAG API 路由 ====================
from src.smartdocrag.api import rag_router, auth_router
app.include_router(rag_router)
app.include_router(auth_router)


# ==================== 基础路由 ====================
@app.get("/", tags=["健康检查"])
async def root():
    """根路径欢迎信息"""
    return {
        "message": f"欢迎使用 {settings.APP_NAME} v{settings.APP_VERSION}",
        "status": "running",
        "docs": "/docs"
    }


@app.get("/health", tags=["健康检查"])
async def health_check():
    """健康检查接口（部署和监控常用）"""
    return {
        "status": "healthy",
        "app_name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "debug": settings.DEBUG,
        "timestamp": time.time()
    }


@app.get("/config", tags=["调试"])
async def get_config():
    """返回当前配置（仅 DEBUG 模式下可用，生产时应删除或加权限）"""
    if not settings.DEBUG:
        return JSONResponse(
            status_code=403,
            content={"detail": "Config endpoint is disabled in production"}
        )

    # 只返回非敏感配置
    safe_config = {
        "app_name": settings.APP_NAME,
        "app_version": settings.APP_VERSION,
        "embedding_model": settings.EMBEDDING_MODEL,
        "llm_model": settings.LLM_MODEL,
        "chunk_size": settings.CHUNK_SIZE,
        "top_k": settings.TOP_K,
        "debug": settings.DEBUG,
    }
    return safe_config


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "src.smartdocrag.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG
    )