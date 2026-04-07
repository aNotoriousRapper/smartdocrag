from llama_index.core import VectorStoreIndex, get_response_synthesizer, Settings
from llama_index.llms.openai_like import OpenAILike  # ← 改用这个
from llama_index.vector_stores.chroma import ChromaVectorStore
from llama_index.core.query_engine import RetrieverQueryEngine
from llama_index.core.retrievers import VectorIndexRetriever
from sqlalchemy import make_url
import logging

from src.smartdocrag.core.config import settings

logger = logging.getLogger(__name__)


class RAGQueryEngine:
    """RAG 查询引擎"""

    def __init__(self):
        # LLM 使用 OpenAILike 支持千问
        self.llm = OpenAILike(
            api_base=settings.LLM_API_BASE.rstrip('/'),
            api_key=settings.LLM_API_KEY,
            model=settings.LLM_MODEL,
            temperature=0.1,
            max_tokens=2048,
            is_chat_model=True,
        )
        Settings.llm = self.llm

        # Chroma 配置（与 ingestion 保持一致）
        import chromadb
        self.client = chromadb.PersistentClient(path="./chroma_db")
        self.collection = self.client.get_or_create_collection("smartdocrag_default")

        self.vector_store = ChromaVectorStore(chroma_collection=self.collection)

        self.index = VectorStoreIndex.from_vector_store(
            vector_store=self.vector_store,
        )

        self.retriever = VectorIndexRetriever(
            index=self.index,
            similarity_top_k=settings.TOP_K,
        )

        self.response_synthesizer = get_response_synthesizer(
            llm=self.llm,
            response_mode="compact"
        )

        self.query_engine = RetrieverQueryEngine(
            retriever=self.retriever,
            response_synthesizer=self.response_synthesizer,
        )

        logger.info(f"✅ 查询引擎初始化完成 - 模型: {settings.LLM_MODEL} (使用 Chroma)")

    # query 方法保持不变
    def query(self, question: str):
        if not settings.LLM_API_KEY.strip():
            return {"error": "LLM_API_KEY 未设置，请检查 .env 文件"}

        try:
            response = self.query_engine.query(question)

            sources = []
            if hasattr(response, 'source_nodes'):
                for node in response.source_nodes[:5]:
                    sources.append({
                        "file_name": node.metadata.get("file_name", "未知"),
                        "score": round(float(node.score), 4) if hasattr(node, 'score') else None,
                        "text_preview": node.text[:150] + "..." if len(node.text) > 150 else node.text
                    })

            return {
                "answer": str(response),
                "sources": sources,
                "metadata": {"model": settings.LLM_MODEL, "top_k": settings.TOP_K}
            }
        except Exception as e:
            logger.error(f"查询失败: {e}")
            return {"error": f"查询出错: {str(e)}"}


# 全局单例
query_engine = RAGQueryEngine()