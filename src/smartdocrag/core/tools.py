from langchain_openai import ChatOpenAI
from ragas.llms import LangchainLLMWrapper

from config import settings


def GetOpenAILLM():
    lc_llm = ChatOpenAI(base_url=settings.LLM_API_BASE.rstrip('/'),
                        api_key=settings.LLM_API_KEY,
                        model=settings.LLM_MODEL,
                        temperature=0.0,
                        max_tokens=2048)
    ragas_llm = LangchainLLMWrapper(lc_llm)
    return ragas_llm