from llama_index.core import PromptTemplate
from typing import List, Dict
import json
from tqdm import tqdm
import asyncio


class QAGenerator:
    """基于 LLM 自动生成高质量问答对"""

    def __init__(self, llm):
        self.llm = llm

        # 优化后的 QA 生成 Prompt
        self.qa_prompt = PromptTemplate(
            """你是一个专业的编程技术专家。
            请基于以下提供的技术文档内容，生成 6-8 个高质量、多样化的问答对。
            
            文档内容：
            {context}
            
            生成要求：
            - 问题类型要多样：包含基础事实型、语义改写型、推理型、边界/否定型问题
            - 答案必须严格基于文档内容，不能添加任何外部知识
            - 每个答案都要简洁、准确，并尽可能引用具体段落
            - 问题要自然、专业，像真实用户会问的问题
            
            请以严格的 JSON 数组格式输出，不要添加任何额外解释。
            
            输出格式示例：
            ```json
            [
              {{
                "question": "这里写问题",
                "answer": "这里写答案", 
                "type": "fact|rewrite|reasoning|boundary",
                "reference": "引用文档中的关键句子"
              }}
            ]
            """
        )

    async def generate_from_text(self, text: str, num_pairs: int = 6) -> List[Dict]:
        """从一段文本生成 QA 对"""
        if not text or len(text.strip()) < 50:
            return []
        prompt = self.qa_prompt.format(context=text)
        try:
            response = await self.llm.acomplete(prompt)
            text_response = response.text.strip()
            # 提取 JSON 部分
            if "json" in text_response:
                json_str = text_response.split("json")[1].split("```")[0].strip()
            else:
                json_str = text_response
            qa_pairs = json.loads(json_str)
            # 限制数量并返回
            return qa_pairs[:num_pairs]
        except json.JSONDecodeError:
            print("JSON 解析失败，跳过此段文本")
            return []
        except Exception as e:
            print(f"生成 QA 对失败: {e}")
            return []

    async def generate_from_documents(self, documents: List, max_pairs_per_doc: int = 6) -> List[Dict]:
        """从多个文档批量生成 QA 对"""
        all_qa_pairs = []
        print(f"开始从 {len(documents)} 个文档片段生成 QA 对...")
        for doc in tqdm(documents, desc="生成 QA 对"):
            qa_pairs = await self.generate_from_text(doc.text, max_pairs_per_doc)
            for qa in qa_pairs:
                qa.update({
                    "source_file": doc.metadata.get("file_name", "unknown"),
                    "chunk_id": doc.metadata.get("id", ""),
                    "document_type": doc.metadata.get("document_type", "legal")
                })
                all_qa_pairs.append(qa)
        print(f"共生成 {len(all_qa_pairs)} 个 QA 对")
        return all_qa_pairs