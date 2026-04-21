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

## 1️⃣ 问题测试（Query Testing）

用于验证 RAG 系统的实际问答效果，是最核心的交互入口。

<!-- screenshot -->

功能说明：

输入用户问题，触发 RAG 检索 + LLM 生成
返回最终答案（Answer）
可扩展展示：
检索到的上下文（Context）
相似度 / Top-K 文档
支持快速迭代 Prompt 和检索策略

适用场景：

验证知识库是否生效
调试召回质量（recall）
观察 hallucination（幻觉）情况
