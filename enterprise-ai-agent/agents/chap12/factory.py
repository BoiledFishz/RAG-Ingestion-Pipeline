"""Wiring for the Chap12 Supervisor; no clients are created at import time."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from rag.techqa.data import ROOT

from agents.chap12.budget import BudgetedModel, BudgetLimits
from agents.chap12.db_worker import DatabaseQueryWorker
from agents.chap12.judged_selector import JudgedSelector
from agents.chap12.ollama_tokens import TokenMeteredOllamaModel
from agents.chap12.product_pick import ProductPicker, pick_mode
from agents.chap12.rag_worker import RagWorker
from agents.chap12.strict_selector import StrictSelector, selector_mode
from agents.chap12.supervisor import Supervisor
from agents.chap12.verifier import AnswerVerifier
from agents.rag_agent.compression import ContextCompressor
from agents.rag_agent.generation import EvidenceSelector, ExtractiveSelector, LLMSelector
from agents.rag_agent.rewrite import LLMRewriter, QueryRewriter, RuleRewriter
from agents.rag_agent.service import RAGAgent
from models.settings import Settings

DEFAULT_INDEX = ROOT / ".rag_data/chap12_sample.sqlite"
# Online-profile settings chosen on the tune split with the real model
# (evaluation/chap12_tune_decide.py). Absent file = Project 1 defaults.
TUNED = Path(__file__).resolve().parents[2] / "evaluation/chap12/tune/real_config.json"
ENV_KEYS = {"top_k": "AGENT_TOP_K", "max_context_tokens": "AGENT_MAX_CONTEXT_TOKENS",
            "model": "AGENT_MODEL"}  # model: round 5 (adopted only if 14b passes its rule)


def tuned_config() -> dict[str, Any]:
    if not TUNED.is_file():
        return {}
    import json

    data: dict[str, Any] = json.loads(TUNED.read_text(encoding="utf-8")).get("adopted", {})
    return data


def apply_tuned(settings: Settings) -> Settings:
    """Online profile only; an explicit environment variable always wins."""
    if settings.profile == "offline":
        return settings
    update = {k: v for k, v in tuned_config().items()
              if k in ENV_KEYS and os.getenv(ENV_KEYS[k]) is None}
    return settings.model_copy(update=update) if update else settings


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


def build_rag_agent(settings: Settings, path: Path, override: Any | None = None,
                    tuned: bool = True) -> RAGAgent:
    """The Project 1 agent, unchanged, over the sample retriever, with metered model calls.

    tuned=False keeps the Project 1 settings (used for the p1_single baseline)."""
    if tuned:
        settings = apply_tuned(settings)
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
        controlled = os.getenv("TECHQA_GENERATION", "extractive") == "controlled"
        # Round 7: strict answerability selector (Project 2 subclass), only when chosen on
        # the tune split or forced by CHAP12_SELECTOR; tuned=False keeps Project 1's selector.
        mode = selector_mode(tuned_config().get("selector") if tuned else None)
        if tuned and mode == "strict":
            selector = StrictSelector(model, controlled=controlled)
        elif tuned and mode == "judged":  # round 8: select, then a separate judge call
            selector = JudgedSelector(model, controlled=controlled)
        else:
            selector = LLMSelector(model, controlled=controlled)
        # Reranker chosen on the tune split (round 3); CHAP12_RERANKER always wins.
        chosen = tuned_config().get("reranker") if tuned and \
            os.getenv("CHAP12_RERANKER") is None else None
        retriever = override or SampleRetrieverTool(
            path, rerank=None if chosen in (None, "nomic") else str(chosen))
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
    picker = None
    mode = pick_mode()
    if settings.profile != "offline" and mode != "off":
        # Same model as the RAG Worker, metered against the same request budget.
        picker = ProductPicker(BudgetedModel(
            TokenMeteredOllamaModel(settings.ollama_url, settings.model, settings.llm_timeout)))
    database = DatabaseQueryWorker(path, statement_timeout=float(
        os.getenv("CHAP12_DB_STATEMENT_TIMEOUT", "10")), picker=picker, pick_mode=mode)
    rag = RagWorker(build_rag_agent(settings, path), timeout=limits.deadline_seconds - 5)
    critic = tuned_config().get("critic") if settings.profile != "offline" else None
    verifier = verify = verify_min = None
    if settings.profile != "offline":
        # Same model as the RAG Worker, metered against the same request budget (round 5).
        verifier = AnswerVerifier(BudgetedModel(
            TokenMeteredOllamaModel(settings.ollama_url, settings.model, settings.llm_timeout)))
        verify = tuned_config().get("verifier")
        verify_min = tuned_config().get("verifier_min_score")  # graded (round 6)
    return Supervisor({"rag": rag, "database": database}, database.catalog, limits,
                      critic=critic, verifier=verifier, verify=verify, verify_min=verify_min)
