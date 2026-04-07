from llama_index.core import VectorStoreIndex, StorageContext, Document, Settings
from llama_index.core.node_parser import SentenceSplitter
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.vector_stores.chroma import ChromaVectorStore
import chromadb
import logging
from pathlib import Path
from typing import List

from src.smartdocrag.core.config import settings

logger = logging.getLogger(__name__)


class RAGIngestion:
    """文档摄入管道 - 使用 Chroma（临时绕过 pgvector 编码问题）"""

    def __init__(self):
        # 全局设置嵌入模型
        self.embed_model = HuggingFaceEmbedding(
            model_name=settings.EMBEDDING_MODEL,
            trust_remote_code=True,
            device="cpu"
        )
        Settings.embed_model = self.embed_model

        # Chroma 配置（持久化到本地文件夹）
        self.persist_dir = "./chroma_db"
        self.client = chromadb.PersistentClient(path=self.persist_dir)

        # 创建或获取 collection（用户隔离用 collection_name）
        self.collection = self.client.get_or_create_collection("smartdocrag_default")

        self.vector_store = ChromaVectorStore(chroma_collection=self.collection)
        self.storage_context = StorageContext.from_defaults(vector_store=self.vector_store)

        self.text_splitter = SentenceSplitter(
            chunk_size=settings.CHUNK_SIZE,
            chunk_overlap=settings.CHUNK_OVERLAP
        )

        logger.info(f"✅ Chroma 向量存储初始化完成 (persist_dir: {self.persist_dir})")

    def ingest_documents(self, file_paths: List[str], collection_name: str = "default") -> int:
        documents = []
        for path_str in file_paths:
            path = Path(path_str)
            if not path.exists():
                logger.warning(f"文件不存在: {path}")
                continue

            try:
                with open(path, "r", encoding="utf-8") as f:
                    text = f.read()

                doc = Document(
                    text=text,
                    metadata={
                        "file_name": path.name,
                        "file_path": str(path),
                        "collection": collection_name
                    }
                )
                documents.append(doc)
                logger.info(f"已加载文档: {path.name}")
            except Exception as e:
                logger.error(f"读取文件失败 {path}: {e}")

        if not documents:
            logger.warning("没有找到有效文档")
            return 0

        # 创建索引
        index = VectorStoreIndex.from_documents(
            documents,
            storage_context=self.storage_context,
            embed_model=self.embed_model,
            transformations=[self.text_splitter]
        )

        logger.info(f"✅ 成功摄入 {len(documents)} 个文档")
        return len(documents)


# 全局单例
ingestion_pipeline = RAGIngestion()