from typing import List, Dict
import re
import hashlib


class DataCleaner:
    """
    QA 对数据清洗与质量控制模块
    """

    @staticmethod
    def clean_qa_pairs(qa_pairs: List[Dict]) -> List[Dict]:
        """
        对生成的 QA 对进行清洗和质量过滤
        """
        if not qa_pairs:
            return []

        cleaned = []
        seen = set()  # 用于去重

        for qa in qa_pairs:
            try:
                question = qa.get("question", "").strip()
                answer = qa.get("answer", "").strip()
                qa_type = qa.get("type", "unknown")

                # 基础过滤：长度检查
                if len(question) < 8 or len(answer) < 10:
                    continue

                # 去重（基于 question + answer 的哈希）
                content_hash = hashlib.md5(f"{question}{answer}".encode()).hexdigest()
                if content_hash in seen:
                    continue
                seen.add(content_hash)

                # 质量过滤：过滤低质量答案
                bad_phrases = [
                    "无法回答", "不知道", "根据上下文", "没有找到",
                    "无法确定", "请提供更多", "我不清楚"
                ]
                if any(phrase in answer for phrase in bad_phrases):
                    continue

                # 类型规范化
                valid_types = {"fact", "rewrite", "reasoning", "boundary"}
                if qa_type not in valid_types:
                    qa_type = "fact"

                # 构建清洗后的 QA 对
                cleaned_qa = {
                    "question": question,
                    "answer": answer,
                    "type": qa_type,
                    "reference": qa.get("reference", ""),
                    "source_file": qa.get("source_file", "unknown"),
                    "chunk_id": qa.get("chunk_id", ""),
                    "document_type": qa.get("document_type", "legal")
                }

                cleaned.append(cleaned_qa)

            except Exception as e:
                # 单个 QA 对出错不影响整体
                continue

        # 按类型均衡采样（可选）
        cleaned = DataCleaner._balance_by_type(cleaned)

        return cleaned

    @staticmethod
    def _balance_by_type(qa_pairs: List[Dict]) -> List[Dict]:
        """
        尽量让不同类型的问题分布均衡
        """
        from collections import defaultdict
        type_groups = defaultdict(list)

        for qa in qa_pairs:
            qa_type = qa.get("type", "fact")
            type_groups[qa_type].append(qa)

        balanced = []
        min_count = min(len(group) for group in type_groups.values()) if type_groups else 0

        for group in type_groups.values():
            balanced.extend(group[:min_count + 2])  # 每种类型至少多保留2个

        return balanced

    @staticmethod
    def filter_by_quality(qa_pairs: List[Dict], min_answer_length: int = 15) -> List[Dict]:
        """额外质量过滤"""
        return [
            qa for qa in qa_pairs
            if len(qa.get("answer", "")) >= min_answer_length
        ]

    @staticmethod
    def save_to_file(qa_pairs: List[Dict], filepath: str = "evaluation/cleaned_qa.json"):
        """保存清洗后的 QA 数据"""
        import json
        from pathlib import Path

        Path("evaluation").mkdir(exist_ok=True)

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(qa_pairs, f, ensure_ascii=False, indent=2)

        print(f"已保存 {len(qa_pairs)} 个清洗后的 QA 对到 {filepath}")