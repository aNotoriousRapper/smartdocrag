from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List, Optional
import shutil
import os
from pathlib import Path
import logging

from src.smartdocrag.core.config import settings
from src.smartdocrag.rag.ingestion import ingestion_pipeline
from src.smartdocrag.rag.query_engine import query_engine

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["RAG"])


# ====================== 请求模型 ======================
class QueryRequest(BaseModel):
    question: str
    debug: bool = False
    top_k: Optional[int] = None


class QueryResponse(BaseModel):
    answer: str
    sources: List[dict]
    metadata: dict


# ====================== 辅助函数 ======================
def save_uploaded_file(upload_file: UploadFile, save_dir: str = "uploads") -> str:
    """保存上传的文件"""
    Path(save_dir).mkdir(exist_ok=True)
    file_path = Path(save_dir) / upload_file.filename

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(upload_file.file, buffer)

    return str(file_path)


# ====================== API 接口 ======================

@router.post("/ingest", summary="上传文档并摄入 RAG 系统")
async def ingest_documents(
        background_tasks: BackgroundTasks,
        files: List[UploadFile] = File(...),
        collection: str = Query("default", description="文档集合名称，用于多用户隔离")
):
    """支持多文件上传，异步处理文档摄入"""
    if not files:
        raise HTTPException(status_code=400, detail="没有上传文件")

    saved_files = []
    try:
        for file in files:
            if not file.filename.lower().endswith(('.txt', '.md', '.pdf', '.docx')):
                raise HTTPException(status_code=400, detail=f"不支持的文件类型: {file.filename}")

            file_path = save_uploaded_file(file)
            saved_files.append(file_path)

        # 异步执行文档摄入（避免阻塞 API）
        background_tasks.add_task(
            ingestion_pipeline.ingest_documents,
            saved_files,
            collection_name=collection
        )

        return {
            "status": "success",
            "message": f"已接收 {len(files)} 个文件，正在后台处理...",
            "files": [f.filename for f in files],
            "collection": collection
        }

    except Exception as e:
        logger.error(f"摄入文件失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/query", response_model=QueryResponse, summary="智能问答接口")
async def query_documents(request: QueryRequest):
    """核心问答接口"""
    try:
        # 支持动态修改 top_k
        if request.top_k and request.top_k != settings.TOP_K:
            # 临时修改（实际生产中建议用不同 query_engine 实例）
            pass

        result = query_engine.query(
            question=request.question,
            debug=request.debug
        )

        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])

        return QueryResponse(
            answer=result["answer"],
            sources=result["sources"],
            metadata=result["metadata"]
        )

    except Exception as e:
        logger.error(f"查询失败: {e}")
        raise HTTPException(status_code=500, detail=f"查询失败: {str(e)}")


@router.get("/documents", summary="查看已摄入的文档列表")
async def list_documents():
    """简单返回 Chroma 中存储的文档数量（演示用）"""
    try:
        count = len(ingestion_pipeline.client.get_collection("smartdocrag_default").peek()["ids"])
        return {
            "status": "success",
            "total_documents": count,
            "message": "文档数量统计（简化版）"
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}