"""Wiring for the Chap12 Supervisor; no clients are created at import time."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from rag.techqa.data import ROOT

from agents.chap12.budget import BudgetedModel, BudgetLimits
from agents.chap12.db_worker import DatabaseQueryWorker
from agents.chap12.ollama_tokens import TokenMeteredOllamaModel
from agents.chap12.rag_worker import RagWorker
from agents.chap12.supervisor import Supervisor
from agents.rag_agent.compression import ContextCompressor
from agents.rag_agent.generation import EvidenceSelector, ExtractiveSelector, LLMSelector
from agents.rag_agent.rewrite import LLMRewriter, QueryRewriter, RuleRewriter
from agents.rag_agent.service import RAGAgent
from models.settings import Settings

DEFAULT_INDEX = ROOT / ".rag_data/chap12_sample.sqlite"


def index_path() -> Path:
    return Path(os.getenv("CHAP12_INDEX_PATH", str(DEFAULT_INDEX)))


def budget_limits() -> BudgetLimits:
    return BudgetLimits(
        deadline_seconds=float(os.getenv("CHAP12_DEADLINE_SECONDS", "150")),
        max_llm_calls=int(os.getenv("CHAP12_MAX_LLM_CALLS", "8")),
        max_embedding_calls=int(os.getenv("CHAP12_MAX_EMBEDDING_CALLS", "4")),
        max_db_queries=int(os.getenv("CHAP12_MAX_DB_QUERIES", "4")),
        max_tool_calls=int(os.getenv("CHAP12_MAX_TOOL_CALLS", "4")),
        max_sql_statements=int(os.getenv("CHAP12_MAX_SQL_STATEMENTS", "400")),
        max_local_compute=int(os.getenv("CHAP12_MAX_LOCAL_COMPUTE", "16")),
    )


def build_rag_agent(settings: Settings, path: Path, override: Any | None = None) -> RAGAgent:
    """The Project 1 agent, unchanged, over the sample retriever, with metered model calls."""
    from tools.sample_retriever import SampleRetrieverTool

    rewriter: QueryRewriter
    selector: EvidenceSelector
    if settings.profile == "offline":
        rewriter, selector = RuleRewriter(), ExtractiveSelector()
        # No model service offline: MiniLM rerank over stored vectors when the sidecar exists.
        offline = "minilm" if path.with_suffix(".dense.sqlite").is_file() else "lexical"
        retriever = override or SampleRetrieverTool(
            path, rerank=os.getenv("CHAP12_RERANKER", offline))
    else:
        model = BudgetedModel(
            TokenMeteredOllamaModel(settings.ollama_url, settings.model, settings.llm_timeout))
        rewriter = LLMRewriter(model)
        selector = LLMSelector(
            model, controlled=os.getenv("TECHQA_GENERATION", "extractive") == "controlled")
        retriever = override or SampleRetrieverTool(path)
    return RAGAgent(
        rewriter=rewriter, selector=selector, retriever=retriever,
        compressor=ContextCompressor(settings.max_context_tokens, settings.max_sources,
                                     settings.min_relevance,
                                     model_selects_evidence=settings.profile == "ollama"),
        top_k=settings.top_k,
    )


def build_supervisor(settings: Settings | None = None, path: Path | None = None) -> Supervisor:
    settings = settings or Settings.from_env()
    path = path or index_path()
    limits = budget_limits()
    database = DatabaseQueryWorker(path, statement_timeout=float(
        os.getenv("CHAP12_DB_STATEMENT_TIMEOUT", "10")))
    rag = RagWorker(build_rag_agent(settings, path), timeout=limits.deadline_seconds - 5)
    return Supervisor({"rag": rag, "database": database}, database.catalog, limits)
