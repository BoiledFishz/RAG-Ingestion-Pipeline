"""Agentic tools share the same official TechQA corpus as the other applications."""

from __future__ import annotations

import asyncio
import os
from typing import Any

from rag.techqa.retrieval import build_pipeline, open_index
from rag.techqa.settings import acceptance_score, evidence_candidate_threshold

from models.schemas import Document


class TechQAStore:
    def __init__(self) -> None:
        self.index = open_index()
        self.pipeline = build_pipeline(final_k=int(os.getenv("TECHQA_AGENT_CANDIDATE_K", "20")))

    @staticmethod
    def convert(doc: dict[str, Any], score: float = 0, excerpt: str = "") -> Document:
        return Document(
            document_id=doc["id"],
            title=doc["title"],
            text=doc["text"],
            source=f"techqa://{doc['id']}",
            score=score,
            retrieved_excerpt=excerpt.removeprefix(doc["title"] + "\n\n"),
        )

    async def search(self, query: str, top_k: int) -> list[Document]:
        outcome = await self.pipeline.retrieve(query, mode="hybrid")
        output, seen = [], set()
        for result in outcome.results:
            score, threshold = acceptance_score(
                query,
                result.text,
                result.score,
                fallback=outcome.diagnostics.reranker_fallback,
            )
            if score < min(threshold, evidence_candidate_threshold()):
                continue
            doc_id = str(result.metadata["techqa_document_id"])
            if doc_id in seen:
                continue
            seen.add(doc_id)
            doc = await asyncio.to_thread(self.index.get, doc_id)
            if doc:
                output.append(self.convert(doc, score, result.text))
        return output[:top_k]


class TechQASearchTool:
    name = "search"
    description = "Search the full official TechQA corpus with BM25 for additional evidence."

    def __init__(self, store: TechQAStore) -> None:
        self.store = store

    async def invoke(self, query: str, limit: int = 5) -> list[Document]:
        outcome = await self.store.pipeline.retrieve(query, mode="sparse")
        output = []
        for result in outcome.results:
            score, threshold = acceptance_score(
                query,
                result.text,
                result.score,
                fallback=outcome.diagnostics.reranker_fallback,
                mode="sparse",
            )
            if score < min(threshold, evidence_candidate_threshold()):
                continue
            doc = await asyncio.to_thread(
                self.store.index.get,
                str(result.metadata["techqa_document_id"]),
            )
            if doc:
                output.append(self.store.convert(doc, score, result.text))
        return output[:limit]


class TechQADocumentTool:
    name = "read_document"
    description = "Read an observed official TechQA document by its original IBM document ID."

    def __init__(self, store: TechQAStore) -> None:
        self.store = store

    async def invoke(self, document_id: str) -> Document | None:
        doc = await asyncio.to_thread(self.store.index.get, document_id)
        return self.store.convert(doc) if doc else None
