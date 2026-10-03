"""Full MiniLM semantic retrieval, shared BM25 and bounded nomic reranking.

Hash/Qdrant retrieval is an explicitly selected historical baseline only.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
import re
import sqlite3
from contextlib import closing
from dataclasses import replace
from pathlib import Path
from typing import Any

from rag.ingestion.models import MetadataValue
from rag.ingestion.providers import HashEmbeddingProvider, OllamaEmbeddingProvider
from rag.retrieval.contracts import SearchResult
from rag.retrieval.filters import FilterPolicy, metadata_matches
from rag.retrieval.pipeline import RetrievalConfig, RetrievalPipeline
from rag.techqa.data import INDEX_PATH, ROOT, digest, documents
from rag.techqa.index import TechQAIndex, tokens

LOGGER = logging.getLogger(__name__)


def legacy_chunks(doc: dict[str, Any]) -> list[SearchResult]:
    """Match IDs/offsets of the existing 1200/160 full Qdrant checkpoint exactly.

    New PDF/Markdown ingestion continues to use RecursiveCharacterTextSplitter.
    Compatibility here prevents different identities between full dense and sparse indexes.
    """
    title, body, doc_id = doc["title"], doc["text"], doc["id"]
    text = f"{title}\n\n{body}" if title else body
    output = []
    cursor, number = 0, 0
    while cursor < len(text):
        remaining = text[cursor:]
        end = min(len(remaining), 1200)
        if len(remaining) > 1200:
            for pattern in (r"\n\n+", r"\n", r"(?<=[.!?])\s+", r"\s+"):
                matches = list(re.finditer(pattern, remaining[:1200]))
                if matches and matches[-1].start() >= 600:
                    end = matches[-1].start()
                    break
        chunk = remaining[:end].strip()
        if chunk:
            hashed = digest(chunk)
            meta: dict[str, MetadataValue] = {
                "source_file": f"techqa://{doc_id}",
                "page_number": number + 1,
                "chunk_hash": hashed,
                "chunk_id": f"techqa:{doc_id}:{number}:{hashed[:12]}",
                "techqa_document_id": doc_id,
                "dataset": "IBM TechQA",
                "title": title,
                "language": "en",
                "status": "published",
                "document_type": "ibm_technote",
                "context_summary": title,
                "summary_provider": "official_document_title",
                "chunk_index": number,
                "start_char": cursor,
                "end_char": cursor + end,
                "parent_id": f"techqa:{doc_id}:parent",
            }
            output.append(SearchResult(text=chunk, metadata=meta, score=0, backend="sparse"))
            number += 1
        if cursor + end >= len(text):
            break
        cursor += max(1, end - 160)
    return output


def coverage(query: str, text: str) -> float:
    query_words = set(tokens(query))
    return len(query_words & set(tokens(text))) / max(len(query_words), 1)


class FullSparseRetriever:
    def __init__(self, index: TechQAIndex) -> None:
        self.index = index
        self.policy = FilterPolicy()

    async def retrieve(
        self, query: str, *, limit: int = 30, filters: dict[str, MetadataValue] | None = None
    ) -> list[SearchResult]:
        secure = self.policy.apply(filters)
        if any(
            secure.get(k, v) != v
            for k, v in {
                "language": "en",
                "document_type": "ibm_technote",
                "status": "published",
            }.items()
        ):
            return []
        source = secure.get("source_file")
        if source is not None:
            doc = await asyncio.to_thread(self.index.get, str(source).removeprefix("techqa://"))
            docs = [{**doc, "rank": 1, "bm25_score": 1.0}] if doc else []
        else:
            docs = await asyncio.to_thread(self.index.search, query, limit)
        result: list[SearchResult] = []
        for doc in docs:
            chunks = legacy_chunks(doc)
            if not chunks:
                continue
            chunk = max(chunks, key=lambda c: coverage(query, c.text))
            if not metadata_matches(chunk.metadata, secure):
                continue
            rank = len(result) + 1
            meta = {
                **chunk.metadata,
                "bm25_document_rank": rank,
                "bm25_score": float(doc["bm25_score"]),
            }
            result.append(
                replace(
                    chunk,
                    metadata=meta,
                    score=float(doc["bm25_score"]),
                    retrieval_rank=rank,
                    retrieval_score=float(doc["bm25_score"]),
                    sparse_rank=rank,
                    retrieval_sources=("sparse",),
                )
            )
        return result[:limit]


class HashDenseRetriever:
    def __init__(self, *, url: str | None = None, collection: str | None = None) -> None:
        from qdrant_client import QdrantClient

        self.client = QdrantClient(
            url=url or os.getenv("TECHQA_QDRANT_URL", "http://localhost:6333"),
            timeout=30,
            prefer_grpc=False,
        )
        self.collection = collection or os.getenv("TECHQA_COLLECTION", "techqa_full_hash")
        self.embedder = HashEmbeddingProvider()
        self.policy = FilterPolicy()

    async def retrieve(
        self, query: str, *, limit: int = 30, filters: dict[str, MetadataValue] | None = None
    ) -> list[SearchResult]:
        from qdrant_client.models import FieldCondition, Filter, MatchValue

        secure = self.policy.apply(filters)
        vector = await self.embedder.embed_query(query)
        response = await asyncio.to_thread(
            self.client.query_points,
            self.collection,
            query=vector,
            limit=limit,
            query_filter=Filter(
                must=[FieldCondition(key=k, match=MatchValue(value=v)) for k, v in secure.items()]
            ),
            with_payload=True,
            with_vectors=False,
        )
        results: list[SearchResult] = []
        for point in response.points:
            payload = dict(point.payload or {})
            text = str(payload.pop("text", ""))
            if payload.get("_embedding_id") not in (None, "hash-sha256-384-v1"):
                raise ValueError("Full TechQA collection embedding identity differs")
            meta = {k: v for k, v in payload.items() if isinstance(v, (str, int, float, bool))}
            if not text or not metadata_matches(meta, secure):
                continue
            meta.setdefault("context_summary", str(meta.get("title", "")))
            if meta.get("techqa_document_id"):
                meta.setdefault("parent_id", f"techqa:{meta['techqa_document_id']}:parent")
            rank = len(results) + 1
            results.append(
                SearchResult(
                    text=text,
                    metadata=meta,
                    score=float(point.score),
                    backend="dense",
                    retrieval_rank=rank,
                    retrieval_score=float(point.score),
                    dense_rank=rank,
                    retrieval_sources=("dense",),
                )
            )
        return results


class FullDenseRetriever:
    """Real semantic vectors; Hash is available only as an explicit historical baseline."""

    def __init__(self) -> None:
        self.url = os.getenv("TECHQA_SEMANTIC_URL", "http://127.0.0.1:11435")
        self.policy = FilterPolicy()

    async def retrieve(
        self, query: str, *, limit: int = 30,
        filters: dict[str, MetadataValue] | None = None,
    ) -> list[SearchResult]:
        import httpx

        secure = self.policy.apply(filters)
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(self.url + "/search", json={
                "query": query, "limit": limit, "filters": secure,
            })
            response.raise_for_status()
            data = response.json()
        output = []
        for rank, row in enumerate(data["results"], 1):
            if row["metadata"].get("_embedding_id") != data["embedding_id"]:
                raise ValueError("Query/document semantic identity differs")
            if not metadata_matches(row["metadata"], secure):
                continue
            output.append(SearchResult(
                text=row["text"], metadata=row["metadata"], score=row["score"], backend="dense",
                retrieval_rank=rank, retrieval_score=row["score"], dense_rank=rank,
                retrieval_sources=("dense",),
            ))
        return output


class FixtureDenseRetriever:
    """Offline unit-test adapter over actual, committed TechNotes only."""

    def __init__(self) -> None:
        self.records = [c for doc in documents("fixture") for c in legacy_chunks(doc)]
        self.embedder = HashEmbeddingProvider()
        self.vectors = [self.embedder._embed(c.text) for c in self.records]

    async def retrieve(
        self, query: str, *, limit: int = 30, filters: dict[str, MetadataValue] | None = None
    ) -> list[SearchResult]:
        secure = FilterPolicy().apply(filters)
        vector = await self.embedder.embed_query(query)
        scored = [
            (sum(a * b for a, b in zip(vector, v, strict=True)), c)
            for c, v in zip(self.records, self.vectors, strict=True)
            if metadata_matches(c.metadata, secure)
        ]
        scored.sort(key=lambda item: item[0], reverse=True)
        return [
            replace(
                c,
                backend="dense",
                score=score,
                retrieval_score=score,
                retrieval_rank=rank,
                dense_rank=rank,
                retrieval_sources=("dense",),
            )
            for rank, (score, c) in enumerate(scored[:limit], 1)
        ]


def open_index() -> TechQAIndex:
    if os.getenv("TECHQA_PROFILE", "full") == "fixture":
        from rag.techqa.index import build

        path = ROOT / ".rag_data/techqa_fixture.sqlite"
        build(path, "fixture")
        return TechQAIndex(path)
    return TechQAIndex(INDEX_PATH)


class TechQAParentResolver:
    def __init__(self, index: TechQAIndex) -> None:
        self.index = index

    async def retrieve_by_chunk_ids(self, chunk_ids: list[str]) -> list[SearchResult]:
        result = []
        for key in dict.fromkeys(chunk_ids):
            parts = key.split(":")
            if len(parts) != 3 or parts[0] != "techqa" or parts[2] != "parent":
                continue
            doc = await asyncio.to_thread(self.index.get, parts[1])
            if doc:
                base = legacy_chunks(doc)[0]
                text = doc["title"] + "\n\n" + doc["text"]
                meta = {
                    **base.metadata,
                    "chunk_id": key,
                    "page_number": 1,
                    "chunk_hash": hashlib.sha256(text.encode("utf-8")).hexdigest(),
                }
                meta.pop("parent_id", None)
                result.append(replace(base, text=text, metadata=meta))
        return result


class TechQAReranker:
    """Context-aware ranking; nomic uses cosine, lexical mode is an explicit ablation."""

    def __init__(self, semantic: bool = True) -> None:
        self.semantic = semantic
        self.embedder = OllamaEmbeddingProvider(
            base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
            concurrency=1,
        )
        self.cache = ROOT / ".rag_data/techqa_rerank_cache.sqlite"

    async def embeddings(self, texts: list[str]) -> list[list[float]]:
        self.cache.parent.mkdir(parents=True, exist_ok=True)
        keys = [
            hashlib.sha256((self.embedder.model + ":v1:" + t).encode()).hexdigest() for t in texts
        ]
        with closing(sqlite3.connect(self.cache)) as db:
            db.execute("CREATE TABLE IF NOT EXISTS embeddings (key TEXT PRIMARY KEY, vector TEXT)")
            found = {
                key: json.loads(row[0])
                for key in keys
                if (
                    row := db.execute(
                        "SELECT vector FROM embeddings WHERE key=?", (key,)
                    ).fetchone()
                )
            }
        missing = list(dict.fromkeys(key for key in keys if key not in found))
        if missing:
            vectors = await self.embedder.embed_documents(
                [texts[keys.index(key)] for key in missing]
            )
            found.update(zip(missing, vectors, strict=True))
            with closing(sqlite3.connect(self.cache)) as db:
                db.executemany(
                    "INSERT OR IGNORE INTO embeddings VALUES (?,?)",
                    [(key, json.dumps(found[key])) for key in missing],
                )
                db.commit()
        return [found[key] for key in keys]

    async def rerank(
        self, query: str, candidates: list[SearchResult], *, limit: int = 20
    ) -> list[SearchResult]:
        if not candidates or limit <= 0:
            return []
        semantic_scores = [0.0] * len(candidates)
        if self.semantic:
            vectors = await self.embeddings(
                ["search_query: " + query[:6000]]
                + [
                    "search_document: " + str(c.metadata.get("context_summary", "")) + "\n" + c.text
                    for c in candidates
                ]
            )
            import math

            q = vectors[0]
            for i, v in enumerate(vectors[1:]):
                semantic_scores[i] = sum(a * b for a, b in zip(q, v, strict=True)) / max(
                    math.sqrt(sum(a * a for a in q) * sum(b * b for b in v)), 1e-9
                )
        ranked = []
        for index, candidate in enumerate(candidates):
            title = str(candidate.metadata.get("context_summary", ""))
            lexical = coverage(query, title + " " + candidate.text)
            sparse_rank = int(candidate.metadata.get("bm25_document_rank", 1000))
            prior = 1 / (1 + sparse_rank / 5)
            score = (
                0.50 * semantic_scores[index] + 0.30 * lexical + 0.20 * prior
                if self.semantic
                else 0.55 * lexical + 0.45 * prior
            )
            ranked.append(
                replace(
                    candidate,
                    score=score,
                    rerank_score=score,
                    backend=candidate.backend + "+techqa_rerank",
                )
            )
        ranked.sort(key=lambda result: result.score, reverse=True)
        return [replace(result, rerank_rank=rank) for rank, result in enumerate(ranked[:limit], 1)]


def build_pipeline(
    *, final_k: int = 5, semantic: bool | None = None, index_path: Path | None = None
) -> RetrievalPipeline:
    selected = os.getenv("TECHQA_RERANKER", "nomic") != "lexical" if semantic is None else semantic
    return RetrievalPipeline(
        dense=(
            FixtureDenseRetriever()
            if os.getenv("TECHQA_PROFILE") == "fixture"
            else (HashDenseRetriever() if os.getenv("TECHQA_DENSE_BACKEND") == "hash"
                  else FullDenseRetriever())
        ),
        sparse=FullSparseRetriever(TechQAIndex(index_path) if index_path else open_index()),
        reranker=TechQAReranker(selected),
        config=RetrievalConfig(
            candidate_k=int(os.getenv("RETRIEVAL_CANDIDATE_K", "30")),
            rerank_k=int(os.getenv("RETRIEVAL_RERANK_K", "20")),
            final_k=final_k,
            rrf_rank_constant=int(os.getenv("RRF_RANK_CONSTANT", "60")),
            max_context_tokens=int(os.getenv("MAX_CONTEXT_TOKENS", "8000")),
            max_chunks_per_document=int(os.getenv("MAX_CHUNKS_PER_DOCUMENT", "2")),
            reranker_timeout_seconds=float(os.getenv("TECHQA_RERANKER_TIMEOUT", "120")),
        ),
    )
