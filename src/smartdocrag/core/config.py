from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache
from typing import Optional

class Settings(BaseSettings):
    """项目全局配置类"""

    # ==================== 应用基本信息 ====================
    APP_NAME: str = "SmartDocRAG"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = True
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # ==================== 数据库配置 ====================
    DATABASE_URL: str = "postgresql+psycopg://postgres:postgres@localhost:5432/smartdocrag"

    # ==================== Redis 配置 (Celery 使用) ====================
    REDIS_URL: str = "redis://localhost:6379/0"

    # ==================== JWT 认证 ====================
    SECRET_KEY: str = "your-super-secret-key-change-in-production-please"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24小时

    # ==================== LLM 配置 (OpenAI 兼容接口) ====================
    LLM_API_BASE: str = "https://api.grok.x.ai/v1"
    LLM_API_KEY: str = ""                     # 必须在 .env 中填写
    LLM_MODEL: str = "grok-beta"

    # ==================== 嵌入模型 ====================
    EMBEDDING_MODEL: str = "BAAI/bge-m3"
    EMBEDDING_DIM: int = 1024                 # BGE-M3 的维度

    # ==================== RAG 参数 ====================
    CHUNK_SIZE: int = 1024
    CHUNK_OVERLAP: int = 200
    TOP_K: int = 8
    SIMILARITY_THRESHOLD: float = 0.75

    # Pydantic v2 配置（推荐写法）
    model_config = SettingsConfigDict(
        env_file=".env",           # 自动加载 .env 文件
        env_file_encoding="utf-8",
        extra="ignore",            # 忽略多余的环境变量
        case_sensitive=False,      # 环境变量不区分大小写
    )


# 使用 lru_cache 缓存配置实例（性能更好，避免重复加载）
@lru_cache()
def get_settings() -> Settings:
    """获取配置单例"""
    return Settings()


# 方便直接导入使用
settings = get_settings()