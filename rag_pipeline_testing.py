import os
import asyncio
from pathlib import Path

from src.smartdocrag.core.config import settings
from src.smartdocrag.rag.ingestion import ingestion_pipeline
from src.smartdocrag.rag.query_engine import query_engine


def main():
    print("🚀 SmartDocRAG 最小 RAG Pipeline 测试开始...\n")

    # 1. 准备测试文档
    test_dir = Path("test_documents")
    test_dir.mkdir(exist_ok=True)

    # 创建一个测试 Markdown 文件
    test_file = test_dir / "test_doc.md"
    test_content = """# SmartDocRAG 项目介绍

这是一个用于转行 AI 后端开发的 RAG 系统实战项目。

## 核心技术栈
- FastAPI：高性能异步 Web 框架
- LlamaIndex：强大的 RAG 框架
- PostgreSQL + pgvector：向量数据库
- BGE-M3：优秀的中英双语嵌入模型

## 项目目标
帮助开发者快速构建生产级的智能文档问答系统，并用于简历项目。

作者正在一步一步带领你完成整个系统。
"""

    test_file.write_text(test_content, encoding="utf-8")
    print(f"✅ 测试文档已创建: {test_file}")

    # 2. 文档摄入（Ingestion）
    print("\n📥 开始文档摄入...")
    ingested_count = ingestion_pipeline.ingest_documents([str(test_file)], collection_name="test")
    print(f"✅ 摄入完成，共处理 {ingested_count} 个文档\n")

    # 3. 执行查询
    print("❓ 开始智能查询测试...")
    questions = [
        "这个项目的主要技术栈是什么？",
        "项目的目标是什么？",
        "作者在做什么？"
    ]

    for q in questions:
        print(f"\n问题: {q}")
        result = query_engine.query(q)

        if "error" in result:
            print(f"❌ 错误: {result['error']}")
            continue

        print(f"答案: {result['answer']}")
        print("来源文档:")
        for idx, source in enumerate(result['sources'], 1):
            print(f"  {idx}. {source['file_name']} (相似度: {source.get('score', 'N/A')})")

    print("\n🎉 RAG Pipeline 测试完成！")


if __name__ == "__main__":
    main()