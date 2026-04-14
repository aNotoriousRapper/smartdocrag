import asyncio
from sqlalchemy import text
from src.smartdocrag.core.database import engine, AsyncSessionLocal
from src.smartdocrag.models.user import User
from src.smartdocrag.core.config import settings

import sys

# === Windows 异步兼容性修复 ===
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    print("✅ 已设置 WindowsSelectorEventLoopPolicy（解决 ProactorEventLoop 问题）")

async def test_database_connection():
    print("🚀 开始测试数据库连接...\n")

    try:
        # 测试1: 基础连接 + 执行简单 SQL
        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT 1 as test"))
            print("✅ 数据库基础连接成功！")
            print(f"   返回结果: {result.scalar()}")

        # 测试2: 使用 Session 创建用户表（如果不存在）
        async with AsyncSessionLocal() as session:
            # 检查表是否存在（或直接创建）
            await session.run_sync(lambda sync_session: User.__table__.create(sync_session.bind, checkfirst=True))
            print("✅ 用户表 (users) 检查/创建成功")

            # 测试3: 查询当前用户数量
            result = await session.execute(text("SELECT COUNT(*) FROM users"))
            count = result.scalar()
            print(f"✅ 当前用户表中共有 {count} 条记录")

        print("\n🎉 所有数据库连接测试通过！")
        print(f"数据库地址: {settings.DATABASE_URL}")

    except Exception as e:
        print("\n❌ 数据库连接失败！")
        print(f"错误信息: {str(e)}")
        print("\n请检查以下内容：")
        print("1. Docker 中的 PostgreSQL 是否正在运行？ (docker-compose ps)")
        print("2. DATABASE_URL 是否正确？")
        print("3. 用户名、密码、数据库名是否匹配？")
        raise


if __name__ == "__main__":
    asyncio.run(test_database_connection())