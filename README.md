# SmartDocRAG

生产级智能文档 RAG 问答系统

基于 FastAPI + LlamaIndex + PostgreSQL pgvector 构建，支持 PDF/Word/Markdown 等文档上传、异步处理、向量检索与智能问答。

## 特性
- 异步文档摄入管道（Celery + Redis）
- 用户隔离索引（多租户支持）
- Hybrid Search + 重排序
- JWT 认证与 API 限流
- RAGAS 评估框架
- Docker 一键部署

## 技术栈
- **后端**：FastAPI (Python 3.12)
- **RAG 框架**：LlamaIndex
- **向量数据库**：PostgreSQL + pgvector
- **嵌入模型**：BGE-M3 (中文强)
- **LLM**：Grok / Qwen / DeepSeek (OpenAI 兼容接口)
- **任务队列**：Celery + Redis

## 快速开始

```bash
cp .env.example .env
docker-compose up -d
uvicorn src.smartdocrag.main:app --reload
