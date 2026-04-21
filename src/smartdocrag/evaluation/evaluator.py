import csv
import logging
from typing import List, Dict
from pathlib import Path
import json

from langchain_community.embeddings import HuggingFaceEmbeddings
from tqdm import tqdm

from src.smartdocrag.core import GetOpenAILLM
from src.smartdocrag.core.config import settings
from src.smartdocrag.evaluation.qa_generator import QAGenerator
from src.smartdocrag.evaluation.data_cleaner import DataCleaner  # 我们下一小步会创建
from ragas import evaluate
from ragas.metrics import faithfulness, answer_relevancy, context_precision, context_recall
from datasets import Dataset


class RAGEvaluator:
    """RAG 自动化评估闭环"""

    def __init__(self, llm, query_engine):
        self.llm = llm
        self.query_engine = query_engine
        self.qa_generator = QAGenerator(llm)
        self.cleaner = DataCleaner()

    async def build_dataset(self, documents: List, max_pairs_per_doc: int = 6):
        """文档 → 生成 QA → 清洗 → 返回干净数据集"""
        print(f"正在从 {len(documents)} 个文档片段生成 QA 对...")

        raw_qa = await self.qa_generator.generate_from_documents(
            documents,
            max_pairs_per_doc=max_pairs_per_doc
        )

        print("正在进行数据清洗...")
        cleaned_qa = self.cleaner.clean_qa_pairs(raw_qa)

        print(f"生成 {len(raw_qa)} 个 QA 对，清洗后保留 {len(cleaned_qa)} 个高质量 QA 对")

        # 保存原始生成结果（便于调试）
        Path("evaluation").mkdir(exist_ok=True)
        with open("evaluation/generated_qa.json", "w", encoding="utf-8") as f:
            json.dump(cleaned_qa, f, ensure_ascii=False, indent=2)

        return cleaned_qa

    async def run_full_evaluation(self, documents: List, max_pairs_per_doc: int = 6):
        """一键完整闭环评估"""
        # 1. 生成并清洗 QA 数据集
        qa_pairs = await self.build_dataset(documents, max_pairs_per_doc)

        if not qa_pairs:
            return {"error": "没有生成任何有效的 QA 对"}

        # 2. 使用 RAG 系统回答这些问题
        questions = [qa["question"] for qa in qa_pairs]
        ground_truths = [qa["answer"] for qa in qa_pairs]
        answers = []
        contexts = []

        print("正在用 RAG 系统回答生成的问题...")
        for q in tqdm(questions, desc="RAG 回答"):
            logging.info(f"提问的问题是:{q}")
            result = self.query_engine.query(q, debug=True, user_id="zhuang")
            answers.append(result.get("answer", ""))
            # 关键修改：把所有 sources 的 text_preview 合并成一个字符串
            source_texts = []
            for s in result.get("sources", []):
                preview = s.get("text_preview", "")
                if preview:
                    source_texts.append(preview)

            # RAGAS 期望 contexts 是 list[str]，而不是 list[list[str]]
            contexts.append(["\n\n".join(source_texts)])  # 注意这里是 [合并后的字符串]

        # 3. 构建 RAGAS 数据集
        dataset = Dataset.from_dict({
            "question": questions,
            "answer": answers,
            "contexts": contexts,
            "ground_truth": ground_truths
        })

        ragas_embeddings = HuggingFaceEmbeddings(
            model_name=settings.EMBEDDING_MODEL  # BGE-M3
        )

        # 4. 执行 RAGAS 评估
        print("正在运行 RAGAS 评估...")
        result = evaluate(
            dataset=dataset,
            metrics=[faithfulness, answer_relevancy, context_precision, context_recall],
            embeddings=ragas_embeddings,
            llm=GetOpenAILLM()
        )

        print("\n" + "=" * 70)
        print("RAGAS 评估结果")
        print("=" * 70)

        df = result.to_pandas()
        # 构建详细结果
        detailed_results = []
        for i, row in df.iterrows():
            detailed_results.append({
                "question": questions[i],  # 你需要保存测试问题列表
                "answer": row.get("answer", ""),  # 你需要保存模型回答
                "faithfulness": float(row.get("faithfulness", 0)),
                "answer_relevancy": float(row.get("answer_relevancy", 0)),
                "context_precision": float(row.get("context_precision", 0)),
                "context_recall": float(row.get("context_recall", 0))
            })

        #     status: str
        #     message: Optional[str] = None
        #     qa_count: int
        #     summary: Dict
        #     detailed_results: List[Dict]
        #     html_table: Optional[str] = None

        response_data = {
            "status": "success",
            "message":"评估完成",
            "user": "zhuang",
            "summary": {
                "faithfulness": float(df["faithfulness"].mean(skipna=True)),
                "answer_relevancy": float(df["answer_relevancy"].mean(skipna=True)),
                "context_precision": float(df["context_precision"].mean(skipna=True)),
                "context_recall": float(df["context_recall"].mean(skipna=True))
            },
            "qa_count": len(qa_pairs),
            "detailed_results": detailed_results,
            "html_table": df.to_html(index=False)
        }

        with open('history_result.csv', 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([
                float(df["faithfulness"].mean()),
                float(df["answer_relevancy"].mean()),
                float(df["context_precision"].mean()),
                float(df["context_recall"].mean())
            ])


        return response_data