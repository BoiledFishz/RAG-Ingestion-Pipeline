"""Project 1 TechQA retrieval over the Chap12 sample index (BM25 + context rerank + parents).

Reuses the shared sparse retriever, reranker, acceptance thresholds and parent resolver.
The full-corpus MiniLM dense service indexes all 801,996 documents, so it is not used here:
dense hits outside the sample would bypass the sample scope. Mode is therefore `sparse`.
"""

from __future__ import annotations

import os
from dataclasses import replace
from pathlib import Path

from rag.retrieval.pipeline import RetrievalConfig, RetrievalPipeline
from rag.techqa.index import TechQAIndex
from rag.techqa.retrieval import FullSparseRetriever, TechQAParentResolver, TechQAReranker
from rag.techqa.settings import acceptance_score

from agents.chap12.budget import BudgetedEmbedder
from models.schemas import Document, RetrieverInput
from tools.techqa_retriever import TechQARetrieverTool


class _NoDense:
    async def retrieve(self, *args: object, **kwargs: object) -> list[object]:
        return []


class SampleRetrieverTool(TechQARetrieverTool):
    def __init__(self, index_path: Path, *, semantic_rerank: bool | None = None,
                 final_k: int = 20) -> None:
        index = TechQAIndex(index_path)
        semantic = (os.getenv("TECHQA_RERANKER", "nomic") != "lexical"
                    if semantic_rerank is None else semantic_rerank)
        reranker = TechQAReranker(semantic)
        reranker.embedder = BudgetedEmbedder(reranker.embedder)  # type: ignore[assignment]
        self.pipeline = RetrievalPipeline(
            dense=_NoDense(),  # type: ignore[arg-type]
            sparse=FullSparseRetriever(index),
            reranker=reranker,
            config=RetrievalConfig(mode="sparse", candidate_k=30, rerank_k=20, final_k=final_k,
                                   reranker_timeout_seconds=float(
                                       os.getenv("TECHQA_RERANKER_TIMEOUT", "120"))),
        )
        self.parents = TechQAParentResolver(index)

    async def invoke(self, request: RetrieverInput) -> list[Document]:
        filters = self.secure_filters(request.filters)
        outcome = await self.pipeline.retrieve(request.query, mode="sparse", filters=filters)
        parents = await self.parents.retrieve_by_chunk_ids(
            [str(r.metadata["parent_id"]) for r in outcome.results if r.metadata.get("parent_id")]
        )
        by_id = {p.chunk_id: p for p in parents}
        output: list[Document] = []
        for result in outcome.results:
            parent = by_id.get(str(result.metadata.get("parent_id")))
            if parent is None or any(d.chunk_id == parent.chunk_id for d in output):
                continue
            score, threshold = acceptance_score(
                request.query, result.text, result.score,
                fallback=outcome.diagnostics.reranker_fallback,
            )
            expanded = replace(parent, score=score, metadata={
                **parent.metadata, "_full_parent": True, "_acceptance_threshold": threshold,
                "_retrieved_excerpt": result.text,
            })
            output.append(Document(
                chunk_id=expanded.chunk_id, text=expanded.text, source_file=expanded.source_file,
                page_number=expanded.page_number, score=expanded.score,
                metadata=expanded.metadata,
            ))
            if len(output) == request.top_k:
                break
        return output
