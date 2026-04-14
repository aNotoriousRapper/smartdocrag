from llama_index.core import PromptTemplate

# 法律文档专用的 System Prompt（强烈推荐）
LEGAL_SYSTEM_PROMPT = """你是一个专业、严谨的中国法律助手。
你的任务是基于提供的法律上下文，准确回答用户的问题。

回答要求：
1. 必须严格基于提供的上下文内容回答，不要添加任何不在上下文中的信息。
2. 如果上下文无法回答问题，或信息不足，请直接回答：“根据提供的法律上下文，无法找到相关答案。”
3. 回答必须准确、客观、中性，使用正式的法律语言。
4. 必须引用具体法条或条款（如《中华人民共和国刑法》第XXX条）。
5. 回答时请在最后列出来源文件和相关条款（如果有）。
6. 不要使用“可能”、“大概”、“我认为”等模糊表达。

当前上下文来自用户上传的法律文档。
"""

# 查询时使用的 Prompt Template
QUERY_PROMPT_TEMPLATE = PromptTemplate(
    """<|系统|>
{legal_system_prompt}

<|用户问题|>
{query}

<|检索到的法律上下文|>
{context_str}

<|回答要求|>
请根据以上上下文，给出准确、严谨的回答。
如果无法回答，请明确说明。
"""
)

def get_legal_query_prompt(query: str, context_str: str) -> str:
    """生成最终的查询 Prompt"""
    return QUERY_PROMPT_TEMPLATE.format(
        legal_system_prompt=LEGAL_SYSTEM_PROMPT,
        query=query,
        context_str=context_str
    )