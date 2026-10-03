from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from agents.critic import CriticLoop, LLMCritic, LLMGroundedDiagnosisAgent
from agents.planner import LLMPlanner
from agents.rag_agent.service import GroundedAnswerer, RAGAgent, RuleRewriter
from agents.research import LLMResearchPolicy, ReActResearchAgent
from evaluation.demo_model import DemoStructuredModel
from models.llm import MeteredModel, OllamaStructuredModel, StructuredModel
from tools.retriever import RetrieverTool
from vectorstore.techqa import TechQADocumentTool, TechQASearchTool, TechQAStore

ROOT = Path(__file__).resolve().parents[1]


@lru_cache(maxsize=1)
def build_tools() -> tuple[RetrieverTool, TechQASearchTool, TechQADocumentTool]:
    store = TechQAStore()
    return (
        RetrieverTool(store, top_k=int(os.getenv("TECHQA_AGENT_TOP_K", "10"))),
        TechQASearchTool(store),
        TechQADocumentTool(store),
    )


def build_rag() -> RAGAgent:
    rag, _, _ = build_tools()
    return RAGAgent(RuleRewriter(), rag, GroundedAnswerer(model_from_env()))


def build_advanced(
    model: StructuredModel | None = None,
) -> tuple[MeteredModel, LLMPlanner, ReActResearchAgent, CriticLoop]:
    metered = MeteredModel(model or model_from_env())
    rag, search, documents = build_tools()
    planner = LLMPlanner(metered)
    research = ReActResearchAgent(
        rag,
        search,
        documents,
        LLMResearchPolicy(metered),
        metered,
    )
    critic = CriticLoop(LLMGroundedDiagnosisAgent(metered), LLMCritic(metered), metered)
    return metered, planner, research, critic


def model_from_env(provider: str | None = None) -> StructuredModel:
    selected = (provider or os.getenv("MODEL_PROVIDER") or "ollama").casefold()
    if selected == "ollama":
        return OllamaStructuredModel(
            model=os.getenv("OLLAMA_MODEL", "qwen2.5:7b"),
            url=os.getenv("OLLAMA_URL", "http://localhost:11434"),
        )
    if selected == "demo":
        return DemoStructuredModel()
    raise ValueError(f"Unsupported model provider: {selected}")
