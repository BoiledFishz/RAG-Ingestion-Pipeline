"""Dependency wiring without import-time database access."""

from __future__ import annotations

from agents.rag_agent.compression import ContextCompressor
from agents.rag_agent.generation import EvidenceSelector, ExtractiveSelector, LLMSelector
from agents.rag_agent.rewrite import LLMRewriter, QueryRewriter, RuleRewriter
from agents.rag_agent.service import RAGAgent
from models.providers import Embedder, HashEmbedder, OllamaEmbedder, OllamaStructuredModel
from models.settings import Settings
from tools.retriever import RetrieverTool
from tools.techqa_retriever import TechQARetrieverTool
from vectorstore.qdrant import QdrantStore


def build_embedder(settings: Settings) -> Embedder:
    if settings.embedding_provider == "hash" or (
        settings.embedding_provider == "auto" and settings.profile == "offline"
    ):
        return HashEmbedder()
    return OllamaEmbedder(settings.ollama_url, settings.embedding_model, settings.llm_timeout)


def build_agent(settings: Settings, store: QdrantStore | None = None) -> RAGAgent:
    retriever: RetrieverTool
    if settings.retrieval_backend == "techqa":
        retriever = TechQARetrieverTool()
    else:
        if store is None:
            raise ValueError("Legacy retrieval requires a Qdrant store")
        retriever = RetrieverTool(store, build_embedder(settings), settings.tool_timeout)
    rewriter: QueryRewriter
    selector: EvidenceSelector
    if settings.profile == "offline":
        rewriter, selector = RuleRewriter(), ExtractiveSelector()
    else:
        model = OllamaStructuredModel(settings.ollama_url, settings.model, settings.llm_timeout)
        rewriter, selector = LLMRewriter(model), LLMSelector(model)
    return RAGAgent(
        rewriter=rewriter,
        selector=selector,
        retriever=retriever,
        compressor=ContextCompressor(
            settings.max_context_tokens,
            settings.max_sources,
            settings.min_relevance,
            model_selects_evidence=settings.profile == "ollama",
        ),
        top_k=settings.top_k,
    )


def open_store(settings: Settings) -> QdrantStore | None:
    if settings.retrieval_backend == "techqa":
        return None
    return QdrantStore(
        settings.collection,
        path=settings.qdrant_path,
        url=settings.qdrant_url,
        api_key=settings.qdrant_api_key,
    )
