from src.smartdocrag.core.config import get_settings

settings = get_settings()

print(f"✅ 配置加载成功！")
print(f"APP_NAME: {settings.APP_NAME}")
print(f"EMBEDDING_MODEL: {settings.EMBEDDING_MODEL}")
print(f"LLM_MODEL: {settings.LLM_MODEL}")
print(f"DEBUG 模式: {settings.DEBUG}")