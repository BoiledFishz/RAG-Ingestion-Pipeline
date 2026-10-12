"""Project 1 TechQA retrieval over the Chap12 sample index.

Reuses the shared BM25 retriever, RRF fusion, context reranker, acceptance thresholds and
parent resolver. Dense retrieval uses the sample's own copy of the Project 1 MiniLM vectors
(`<index>.dense.sqlite`, see agents/chap12/dense.py); the full-corpus dense service is not used
because its hits fall outside the sample. Without a sidecar the mode is `sparse`.
"""

from __future__ import annotations

import json
import os
from dataclasses import replace
from pathlib import Path
from typing import Any

from rag.retrieval.contracts import RetrievalMode
from rag.retrieval.pipeline import RetrievalConfig, RetrievalPipeline
from rag.techqa.retrieval import FullSparseRetriever, TechQAParentResolver
from rag.techqa.settings import acceptance_score

from agents.chap12.budget import BudgetedEmbedder
from agents.chap12.metered import CountingReranker, MeteredIndex
from agents.chap12.rag_worker import doc_id
from agents.chap12.scope import PRODUCT_SCOPE, DocumentScope, ScopedRetriever
from models.schemas import Document, RetrieverInput
from tools.techqa_retriever import TechQARetrieverTool

THRESHOLDS = Path(__file__).resolve().parents[1] / "evaluation/chap12/tune/thresholds.json"


def minilm_threshold() -> float:
    """Acceptance threshold for MiniLM rerank scores, calibrated on the tune split only."""
    configured = os.getenv("CHAP12_MINILM_THRESHOLD")
    if configured:
        return float(configured)
    data = json.loads(THRESHOLDS.read_text(encoding="utf-8"))
    return float(data["minilm_rerank"]["threshold"])


SIGNALS = THRESHOLDS.parent / "refusal_signals.json"
REFUSE = 1e9  # finite (metadata must be finite); above any rerank score -> nothing accepted


def refusal_gate() -> float | None:
    """Top-1/top-2 rerank gap gate, only if adopted by the tune-split signal study (D2)."""
    configured = os.getenv("CHAP12_GAP_GATE")
    if configured is not None:
        return float(configured) if configured else None
    if not SIGNALS.is_file():
        return None
    gap = json.loads(SIGNALS.read_text(encoding="utf-8")).get("top1_top2_gap", {})
    return float(gap["best"]["threshold"]) if gap.get("adopt") else None


class _NoDense:
    async def retrieve(self, *args: object, **kwargs: object) -> list[object]:
        return []


class SampleRetrieverTool(TechQARetrieverTool):
    def __init__(self, index_path: Path, *, semantic_rerank: bool | None = None,
                 final_k: int = 20, dense: Any | None = None, use_dense: bool = True,
                 rerank: str | None = None) -> None:
        index = MeteredIndex(index_path)
        self.scope = DocumentScope(index_path)
        sidecar = index_path.with_suffix(".dense.sqlite")
        if dense is None and use_dense and sidecar.is_file():
            from agents.chap12.dense import SampleDenseRetriever

            dense = SampleDenseRetriever(sidecar)
        self.mode: RetrievalMode = "hybrid" if dense is not None else "sparse"
        semantic = (os.getenv("TECHQA_RERANKER", "nomic") != "lexical"
                    if semantic_rerank is None else semantic_rerank)
        # rerank: "nomic" (Ollama embeddings), "lexical" (no model) or "minilm" (stored vectors).
        choice = rerank or os.getenv("CHAP12_RERANKER") or ("nomic" if semantic else "lexical")
        reranker: Any
        self.minilm = False
        if choice == "minilm":
            if dense is None:
                raise ValueError("minilm rerank requires the dense sidecar")
            from agents.chap12.dense import VectorReranker

            reranker = VectorReranker(dense)
            self.minilm = True
        else:
            reranker = CountingReranker(choice == "nomic")
            reranker.embedder = BudgetedEmbedder(reranker.embedder)
        self.pipeline = RetrievalPipeline(
            # Both branches are scoped before fusion/rerank, so unauthorized documents never
            # reach the reranker, the parent resolver or the model.
            dense=ScopedRetriever(dense if dense is not None else _NoDense(), self.scope),
            sparse=ScopedRetriever(FullSparseRetriever(index), self.scope),
            reranker=reranker,
            config=RetrievalConfig(
                mode=self.mode,
                candidate_k=30, rerank_k=20, final_k=final_k,
                reranker_timeout_seconds=float(os.getenv("TECHQA_RERANKER_TIMEOUT", "120"))),
        )
        self.parents = TechQAParentResolver(index)

    async def invoke(self, request: RetrieverInput) -> list[Document]:
        filters = self.secure_filters(request.filters)
        outcome = await self.pipeline.retrieve(request.query, mode=self.mode, filters=filters)
        parents = await self.parents.retrieve_by_chunk_ids(
            [str(r.metadata["parent_id"]) for r in outcome.results if r.metadata.get("parent_id")]
        )
        by_id = {p.chunk_id: p for p in parents}
        output: list[Document] = []
        active = PRODUCT_SCOPE.get()
        gate = refusal_gate() if self.minilm else None
        refuse = False
        if gate is not None and not outcome.diagnostics.reranker_fallback:
            scores = [r.score for r in outcome.results] + [0.0, 0.0]
            # Below the gate no candidate may be accepted: the agent refuses (no_data).
            refuse = scores[0] - scores[1] < gate
        for result in outcome.results:
            if not self.scope.allowed(doc_id(str(result.metadata.get("parent_id", ""))), active):
                raise PermissionError("unauthorized document escaped retrieval scope")
            parent = by_id.get(str(result.metadata.get("parent_id")))
            if parent is None or any(d.chunk_id == parent.chunk_id for d in output):
                continue
            if self.minilm and not outcome.diagnostics.reranker_fallback:
                score, threshold = result.score, (REFUSE if refuse else minilm_threshold())
            else:
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
