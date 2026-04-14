from llama_index.core import VectorStoreIndex, StorageContext, Document, Settings, SimpleDirectoryReader
from llama_index.core.node_parser import SentenceSplitter
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.vector_stores.chroma import ChromaVectorStore
import chromadb
import logging
from pathlib import Path
from typing import List, Optional

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
        self.collection = None
        self.vector_store = None
        self.storage_context = None

        # 创建或获取 collection（用户隔离用 collection_name）
        # self.collection = self.client.get_or_create_collection("smartdocrag_default")

        # self.vector_store = ChromaVectorStore(chroma_collection=self.collection)
        # self.storage_context = StorageContext.from_defaults(vector_store=self.vector_store)

        self.text_splitter = SentenceSplitter(
            chunk_size=settings.CHUNK_SIZE,
            chunk_overlap=settings.CHUNK_OVERLAP
        )

        logger.info(f"✅ RAGIngestion 初始化完成（支持用户隔离）")

    def ingest_documents(self, file_paths: List[str], collection_name: str = "default", user_id: Optional[str] = None) -> int:
        """支持多种文件格式的文档摄入"""
        if not file_paths:
            logger.warning("没有提供文件路径")
            return 0

        """支持用户隔离的文档摄入"""
        if user_id is None:
            user_id = "default"

        # 用户隔离：每个用户一个独立的 collection
        collection_full_name = f"user_{user_id}_{collection_name}"

        try:
            self.collection = self.client.get_or_create_collection(collection_full_name)
            self.vector_store = ChromaVectorStore(chroma_collection=self.collection)
            self.storage_context = StorageContext.from_defaults(vector_store=self.vector_store)
        except Exception as e:
            logger.error(f"创建用户集合失败 {collection_full_name}: {e}")
            return 0

        documents = []

        # 使用 LlamaIndex 内置读取器（推荐方式）
        for path_str in file_paths:
            path = Path(path_str)
            if not path.exists():
                logger.warning(f"文件不存在: {path}")
                continue

            try:
                # SimpleDirectoryReader 可以自动处理 .docx, .pdf, .txt, .md 等
                reader = SimpleDirectoryReader(
                    input_files=[str(path)],
                    filename_as_id=True,
                )
                loaded_docs = reader.load_data()

                # 添加 collection 元数据
                for doc in loaded_docs:
                    doc.metadata.update({
                        "collection": collection_name,
                        "user_id": user_id,
                        "file_name": path.name,
                        "file_path": str(path)
                    })
                    documents.append(doc)

                logger.info(f"✅ 已加载 {len(loaded_docs)} 个片段: {path.name} (用户: {user_id})")

            except Exception as e:
                logger.error(f"读取文件失败 {path.name}: {e}")
                # 失败后尝试 fallback 到纯文本读取（针对 .txt/.md）
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        text = f.read()
                    doc = Document(
                        text=text,
                        metadata={
                            "collection": collection_name,
                            "user_id": user_id,
                            "file_name": path.name
                        }
                    )
                    documents.append(doc)
                    logger.info(f"使用 UTF-8 回退加载: {path.name}")
                except:
                    try:
                        with open(path, "r", encoding="gbk") as f:  # 兼容 GBK
                            text = f.read()
                        doc = Document(
                            text=text,
                            metadata={
                                "collection": collection_name,
                                "user_id": user_id,
                                "file_name": path.name
                            }
                        )
                        documents.append(doc)
                        logger.info(f"使用 GBK 回退加载: {path.name}")
                    except Exception as fallback_e:
                        logger.error(f"所有编码尝试均失败 {path}: {fallback_e}")

        if not documents:
            logger.warning("没有找到任何有效文档")
            return 0

        # 创建索引
        index = VectorStoreIndex.from_documents(
            documents,
            storage_context=self.storage_context,
            embed_model=self.embed_model,
            transformations=[self.text_splitter]
        )

        logger.info(f"🎉 成功摄入 {len(documents)} 个文档片段 (来自 {len(file_paths)} 个文件)")
        return len(documents)


# 全局单例
ingestion_pipeline = RAGIngestion()