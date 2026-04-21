import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict

from fastapi import APIRouter, Depends, HTTPException, status, Query, BackgroundTasks
from pydantic import BaseModel


from src.smartdocrag.auth.dependencies import get_current_user
from src.smartdocrag.evaluation.evaluator import RAGEvaluator
from src.smartdocrag.evaluation.qa_generator import QAGenerator
from src.smartdocrag.rag import ingestion_pipeline
from src.smartdocrag.rag import get_query_engine

logger = logging.getLogger(__name__)

evaluate_router = APIRouter(prefix="/api/v1/evaluate", tags=["Evaluate"])


class QAGenerateRequest(BaseModel):
    num_pairs_per_doc: int = Query(6, ge=3, le=15, description="每个文档生成多少个 QA 对")
    max_docs: Optional[int] = Query(None, description="最多处理多少个文档片段（None 表示全部）")
    user_id: Optional[str] = None   # 如果不传则使用当前登录用户


class QAGenerateResponse(BaseModel):
    status: str
    message: str
    total_generated: int
    qa_pairs: List[dict]
    sample: Optional[List[dict]] = None

class EvaluationRequest(BaseModel):
    max_pairs_per_doc: int = 6
    user_id: Optional[str] = None
    top_k: Optional[int] = None
    prompt: Optional[str] = ""

class EvaluationResponse(BaseModel):
    status: str
    message: Optional[str] = None
    qa_count: int
    summary: Dict
    detailed_results: List[Dict]
    html_table: Optional[str] = None


@evaluate_router.post("/QAGenerate", response_model=QAGenerateResponse)
async def generate_qa_pairs(
        request: QAGenerateRequest,
        engine=Depends(get_query_engine),
        current_user: str = Depends(get_current_user),
        collection: str = Query("default", description="文档集合名称")
):
    """
    根据当前用户上传的文档，自动生成 QA 对
    """
    try:
        # 使用当前登录用户
        user_id = request.user_id or current_user

        # 1. 获取当前用户的所有文档（这里需要你实现获取文档的方法）
        # 注意：你需要从 Chroma 中获取当前用户的文档
        collection_name = f"user_{user_id}_{collection}"

        # 从 Chroma 获取所有文档（这里简化处理，你可以根据实际情况调整）
        collection_obj = ingestion_pipeline.client.get_collection(collection_name)
        all_docs_data = collection_obj.get(include=["documents", "metadatas"])

        if not all_docs_data.get("documents"):
            raise HTTPException(status_code=400, detail="当前用户没有上传任何文档")

        # 限制处理的文档数量
        documents = []
        max_limit = request.max_docs or len(all_docs_data["documents"])

        for i in range(min(max_limit, len(all_docs_data["documents"]))):
            doc_text = all_docs_data["documents"][i]
            metadata = all_docs_data["metadatas"][i] if all_docs_data["metadatas"] else {}

            # 构造 LlamaIndex Document 对象
            from llama_index.core import Document
            doc = Document(
                text=doc_text,
                metadata={
                    **metadata,
                    "user_id": user_id,
                    "collection": collection_name
                }
            )
            documents.append(doc)

        # 2. 初始化 QA 生成器
        qa_generator = QAGenerator(llm=engine.llm)

        # 3. 生成 QA 对
        print(f"开始为用户 {user_id} 生成 QA 对，共 {len(documents)} 个文档片段...")
        qa_pairs = await qa_generator.generate_from_documents(
            documents=documents,
            max_pairs_per_doc=request.num_pairs_per_doc
        )

        # 4. 返回结果
        sample = qa_pairs[:3] if qa_pairs else None  # 返回前3个作为示例

        return {
            "status": "success",
            "message": f"成功为用户 {user_id} 生成 {len(qa_pairs)} 个 QA 对",
            "total_generated": len(qa_pairs),
            "qa_pairs": qa_pairs,
            "sample": sample
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"QA 对生成失败: {str(e)}"
        )


@evaluate_router.post("/full", response_model=EvaluationResponse)
async def run_full_rag_evaluation(
        request: EvaluationRequest,
        background_tasks: BackgroundTasks,
        current_user: str = Depends(get_current_user)
):
    """
    一键完整评估闭环：
    文档 → 生成 QA 对 → 清洗 → RAG 测试 → RAGAS 评估
    """
    try:
        user_id = request.user_id or current_user

        # 初始化评估器

        engine = get_query_engine()
        engine.setTopK(request.top_k)
        engine.setPrompt(request.prompt)
        evaluator = RAGEvaluator(llm=engine.llm, query_engine=engine)

        # 获取当前用户的文档
        collection_name = f"user_{user_id}_default"
        collection = engine.client.get_or_create_collection(collection_name)

        all_docs_data = collection.get(include=["documents", "metadatas"])

        if not all_docs_data.get("documents"):
            raise HTTPException(status_code=400, detail="当前用户没有上传任何文档")

        # 构造 Document 对象
        from llama_index.core import Document
        documents = []
        for i, doc_text in enumerate(all_docs_data["documents"]):
            metadata = all_docs_data["metadatas"][i] if all_docs_data.get("metadatas") else {}
            doc = Document(
                text=doc_text,
                metadata={**metadata, "user_id": user_id}
            )
            documents.append(doc)

        # 执行完整评估闭环（异步）
        result = await evaluator.run_full_evaluation(
            documents=documents,
            max_pairs_per_doc=request.max_pairs_per_doc
        )
        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"评估闭环执行失败: {str(e)}")