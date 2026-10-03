"""Chaînes LangChain (une par fonctionnalité) et agent de chat avec mémoire."""
from functools import lru_cache

from langchain.agents import create_agent

from core.llm import get_llm
from core.schemas import CodeAnalysisResult, GeneratedTestResult, TestExplanationResult
from memory.memory import checkpointer
from prompts.prompts import (
    CHAT_SYSTEM_PROMPT,
    CODE_ANALYSIS_PROMPT,
    TEST_EXPLANATION_PROMPT,
    TEST_GENERATION_PROMPT,
)

STRUCTURED_METHOD = "json_schema"  # repli possible : "function_calling"


def _structured(schema):
    return get_llm().with_structured_output(schema, method=STRUCTURED_METHOD)


@lru_cache(maxsize=1)
def get_analysis_chain():
    """Entrée {"code"} -> CodeAnalysisResult."""
    return CODE_ANALYSIS_PROMPT | _structured(CodeAnalysisResult)


@lru_cache(maxsize=1)
def get_test_chain():
    """Entrée {"code"} -> GeneratedTestResult."""
    return TEST_GENERATION_PROMPT | _structured(GeneratedTestResult)


@lru_cache(maxsize=1)
def get_explain_test_chain():
    """Entrée {"unit_test"} -> TestExplanationResult."""
    return TEST_EXPLANATION_PROMPT | _structured(TestExplanationResult)


@lru_cache(maxsize=1)
def get_chat_agent():
    """Agent de chat libre ; la mémoire est portée par le checkpointer + thread_id."""
    return create_agent(
        model=get_llm(),
        tools=[],
        system_prompt=CHAT_SYSTEM_PROMPT,
        checkpointer=checkpointer,
    )
