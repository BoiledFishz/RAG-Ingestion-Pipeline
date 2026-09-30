from __future__ import annotations

import json
import os
from pathlib import Path

from agents.critic import CriticLoop, LLMCritic, LLMDiagnosisAgent
from agents.planner import LLMPlanner
from agents.rag_agent.service import RAGAgent, RuleRewriter
from agents.research import LLMResearchPolicy, ReActResearchAgent
from evaluation.demo_model import DemoStructuredModel
from models.llm import MeteredModel, OllamaStructuredModel, StructuredModel
from models.schemas import Document
from tools.documents import DocumentRetrievalTool
from tools.retriever import RetrieverTool
from tools.search import SearchTool
from vectorstore.memory import MemoryVectorStore

ROOT = Path(__file__).resolve().parents[1]


def load_documents(name: str) -> list[Document]:
    return [
        Document.model_validate(item)
        for item in json.loads((ROOT / "data" / name).read_text(encoding="utf-8"))
    ]


def build_tools() -> tuple[RetrieverTool, SearchTool, DocumentRetrievalTool]:
    knowledge = load_documents("knowledge.json")
    external = load_documents("external_search.json")
    return (
        RetrieverTool(MemoryVectorStore(knowledge)),
        SearchTool(external),
        DocumentRetrievalTool(knowledge + external),
    )


def build_rag() -> RAGAgent:
    rag, _, _ = build_tools()
    return RAGAgent(RuleRewriter(), rag)


def build_advanced(model: StructuredModel | None = None):
    metered = MeteredModel(model or DemoStructuredModel())
    rag, search, documents = build_tools()
    planner = LLMPlanner(metered)
    research = ReActResearchAgent(
        rag,
        search,
        documents,
        LLMResearchPolicy(metered),
        metered,
    )
    critic = CriticLoop(LLMDiagnosisAgent(metered), LLMCritic(metered), metered)
    return metered, planner, research, critic


def model_from_env(provider: str | None = None) -> StructuredModel:
    selected = (provider or os.getenv("MODEL_PROVIDER", "demo")).casefold()
    if selected == "ollama":
        return OllamaStructuredModel(
            model=os.getenv("OLLAMA_MODEL", "llama3.2:3b"),
            url=os.getenv("OLLAMA_URL", "http://localhost:11434"),
        )
    if selected == "demo":
        return DemoStructuredModel()
    raise ValueError(f"Unsupported model provider: {selected}")
