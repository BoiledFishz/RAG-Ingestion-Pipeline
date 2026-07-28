"""Environment-driven application bootstrap for local and production servers."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from rag.api.routes import create_app
from rag.generation.generator import OllamaGenerator
from rag.generation.service import RAGService
from rag.ingestion.providers import (
    EmbeddingProvider,
    HashEmbeddingProvider,
    OllamaEmbeddingProvider,
)
from rag.ingestion.vector_store import QdrantVectorStore
from rag.retrieval.context_builder import ContextBuilder
from rag.retrieval.dense import DenseRetriever
from rag.retrieval.pipeline import DenseRerankPipeline, RetrievalConfig
from rag.retrieval.reranker import LexicalReranker


def _integer(name: str, default: int) -> int:
    return int(os.getenv(name, str(default)))


def _floating(name: str, default: float) -> float:
    return float(os.getenv(name, str(default)))


def build_service() -> RAGService:
    config = RetrievalConfig(
        mode="dense",
        candidate_k=_integer("RETRIEVAL_CANDIDATE_K", 30),
        rerank_k=_integer("RETRIEVAL_RERANK_K", 20),
        final_k=_integer("RETRIEVAL_FINAL_K", 5),
        rrf_rank_constant=_integer("RRF_RANK_CONSTANT", 60),
        max_context_tokens=_integer("MAX_CONTEXT_TOKENS", 8_000),
        max_chunks_per_document=_integer("MAX_CHUNKS_PER_DOCUMENT", 2),
        reranker_timeout_seconds=_floating("RERANKER_TIMEOUT_SECONDS", 5.0),
        relevance_threshold=_floating("RELEVANCE_THRESHOLD", 0.05),
    )
    store = QdrantVectorStore(
        path=Path(os.getenv("QDRANT_PATH", ".rag_data/qdrant")),
        collection_name=os.getenv("QDRANT_COLLECTION", "aws_support"),
    )
    embedder: EmbeddingProvider
    if os.getenv("EMBEDDING_PROVIDER", "ollama") == "hash":
        embedder = HashEmbeddingProvider()
    else:
        embedder = OllamaEmbeddingProvider(
            model=os.getenv("EMBEDDING_MODEL", "nomic-embed-text"),
            base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
            batch_size=_integer("EMBEDDING_BATCH_SIZE", 32),
            concurrency=_integer("REQUEST_CONCURRENCY", 8),
        )
    dense = DenseRetriever(
        embedder=embedder,
        store=store,
        candidate_k=config.candidate_k,
        final_k=config.final_k,
    )
    return RAGService(
        retriever=DenseRerankPipeline(
            dense=dense,
            reranker=LexicalReranker(),
            config=config,
        ),
        generator=OllamaGenerator(
            model=os.getenv("ANSWER_MODEL", os.getenv("SUMMARY_MODEL", "llama3.2:3b")),
            base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
        ),
        context_builder=ContextBuilder(
            max_context_tokens=config.max_context_tokens,
            max_chunks_per_document=config.max_chunks_per_document,
        ),
        relevance_threshold=config.relevance_threshold,
    )


app: Any = create_app(service=build_service())


def run() -> None:
    try:
        import uvicorn
    except ImportError as exc:
        raise RuntimeError("Install the API dependencies with: pip install -e '.[api]'") from exc
    uvicorn.run("rag.api.runtime:app", host="127.0.0.1", port=8000)
