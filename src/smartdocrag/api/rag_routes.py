from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks, Query, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List, Optional
import shutil
from pathlib import Path
import logging

from src.smartdocrag.core.config import settings
from src.smartdocrag.rag.ingestion import ingestion_pipeline
from src.smartdocrag.rag import get_query_engine
from src.smartdocrag.auth.dependencies import get_current_user

logger = logging.getLogger(__name__)

rag_router = APIRouter(prefix="/api/v1", tags=["RAG"])


class QueryRequest(BaseModel):
    question: str
    debug: bool = False
    top_k: Optional[int] = None


# ====================== 辅助函数 ======================
def save_uploaded_file(upload_file: UploadFile, save_dir: str = "uploads") -> str:
    Path(save_dir).mkdir(exist_ok=True)
    file_path = Path(save_dir) / upload_file.filename
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(upload_file.file, buffer)
    return str(file_path)


# ====================== API 接口 ======================

@rag_router.post("/ingest")
async def ingest_documents(
        background_tasks: BackgroundTasks,
        files: List[UploadFile] = File(...),
        collection: str = Query("default", description="文档集合名称"),
        current_user: str = Depends(get_current_user)  # JWT 认证
):
    """上传文档（需要登录）"""
    if not files:
        raise HTTPException(status_code=400, detail="没有上传文件")

    saved_files = []
    for file in files:
        if not file.filename.lower().endswith(('.txt', '.md', '.pdf', '.docx')):
            raise HTTPException(status_code=400, detail=f"不支持的文件类型: {file.filename}")

        file_path = save_uploaded_file(file)
        saved_files.append(file_path)

    # 异步摄入 + 传入当前用户ID实现隔离
    background_tasks.add_task(
        ingestion_pipeline.ingest_documents,
        saved_files,
        collection_name=collection,
        user_id=current_user
    )

    return {
        "status": "success",
        "message": f"用户 {current_user} 已接收 {len(files)} 个文件，正在后台处理...",
        "collection": f"user_{current_user}_{collection}"
    }


@rag_router.post("/query")
async def query_documents(
        request: QueryRequest,
        engine=Depends(get_query_engine),
        current_user: str = Depends(get_current_user)
):
    """智能问答（需要登录）"""
    try:
        result = engine.query(
            question=request.question,
            debug=request.debug,
            user_id=current_user  # 传入用户ID实现隔离
        )

        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])

        return result
    except Exception as e:
        logger.error(f"查询失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@rag_router.get("/documents")
async def list_documents(collection: str = Query("default", description="文档集合名称"),
                         current_user: str = Depends(get_current_user)):
    """查看当前用户文档数量"""
    try:
        collection_obj = ingestion_pipeline.client.get_collection(f"user_{current_user}_{collection}")

        all_docs = collection_obj.get(include=["metadatas"])
        document_info_dict = {}
        for i, metadata in enumerate(all_docs["metadatas"]):
            file_name = metadata.get("file_name")
            if file_name not in document_info_dict:
                document_info_dict[file_name] = 0
            document_info_dict[file_name] += 1

        return {
            "status": "success",
            "user": current_user,
            "documents_count": len(document_info_dict.keys()),
            "documents_info": document_info_dict
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


@rag_router.delete("/documents/{file_name}", summary="删除指定文档")
async def delete_document(
        file_name: str,
        collection: str = Query("default", description="文档集合名称"),
        current_user: str = Depends(get_current_user),
):
    try:
        collection_name = f"user_{current_user}_{collection}"
        collection_obj = ingestion_pipeline.client.get_collection(collection_name)

        all_docs = collection_obj.get(include=["metadatas"])

        id_to_delete = []
        for i, metadata in enumerate(all_docs["metadatas"]):
            if metadata and metadata.get("file_name") == file_name:
                doc_id = all_docs["ids"][i]
                id_to_delete.append(doc_id)

        if not id_to_delete:
            raise HTTPException(status_code=404, detail=f"未找到文档: {file_name}")

        collection_obj.delete(id_to_delete)
        logger.info(f"用户 {current_user} 删除文档: {file_name}")

        return {
            "status": "success",
            "message": f"成功删除文档 '{file_name}'",
            "deleted_count": 1,
            "user": current_user
        }

    except Exception as e:
        logger.error(f"删除文档失败: {e}")
        raise HTTPException(status_code=500, detail=f"删除失败: {str(e)}")


@rag_router.delete("/documents", summary="删除当前用户所有文档")
async def delete_all_documents(
        collection: str = Query("default", description="文档集合名称"),
        current_user: str = Depends(get_current_user),
):
    try:
        collection_name = f"user_{current_user}_{collection}"
        collection_obj = ingestion_pipeline.client.get_collection(collection_name)

        all_docs = collection_obj.get(include=["metadatas"])

        id_to_delete = []
        document_name_to_delete = []
        for i, metadata in enumerate(all_docs["metadatas"]):
            doc_id = all_docs["ids"][i]
            id_to_delete.append(doc_id)
            file_name = metadata.get("file_name")
            if file_name not in document_name_to_delete:
                document_name_to_delete.append(file_name)

        if len(document_name_to_delete) == 0:
            raise HTTPException(status_code=404, detail=f"未找到任何文档")

        if id_to_delete:
            collection_obj.delete(ids=id_to_delete)


        return {
            "status": "success",
            "message": f"成功删除 {len(document_name_to_delete)} 个文档",
            "deleted_count": len(document_name_to_delete),
            "user": current_user
        }

    except Exception as e:
        logger.error(f"删除文档失败: {e}")
        raise HTTPException(status_code=500, detail=f"删除失败: {str(e)}")