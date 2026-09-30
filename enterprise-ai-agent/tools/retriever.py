"""Agent Retriever Tool wrapping Query Embedding -> Qdrant Search."""

from __future__ import annotations

import asyncio
import logging
import re
from typing import Any

from agents.rag_agent.text import terms
from models.errors import DependencyUnavailable
from models.providers import Embedder
from models.schemas import Document, MetadataValue, RetrieverInput
from vectorstore.qdrant import VectorStore

LOGGER = logging.getLogger(__name__)
ALLOWED_FILTERS = frozenset({"source_file", "document_type", "language", "status"})


class RetrieverTool:
    name = "search_knowledge_base"
    description = "Search published knowledge-base chunks using a bounded vector query."

    def __init__(self, store: VectorStore, embedder: Embedder, timeout: float = 30) -> None:
        self.store, self.embedder, self.timeout = store, embedder, timeout

    @property
    def input_schema(self) -> dict[str, Any]:
        return RetrieverInput.model_json_schema()

    @staticmethod
    def secure_filters(filters: dict[str, MetadataValue]) -> dict[str, MetadataValue]:
        unknown = set(filters) - ALLOWED_FILTERS
        if unknown:
            raise ValueError(f"Unsupported metadata filters: {', '.join(sorted(unknown))}")
        if any(
            not isinstance(value, str) or not value.strip()
            for key, value in filters.items()
            if key != "status"
        ):
            raise ValueError("Metadata filter values must be nonblank strings")
        if filters.get("status", "published") != "published":
            LOGGER.warning("User attempted to override system status filter")
        return {**filters, "status": "published"}

    async def invoke(self, request: RetrieverInput) -> list[Document]:
        filters = self.secure_filters(request.filters)
        if not request.query.strip():
            return []

        async def search() -> list[Document]:
            vector = await self.embedder.embed_query(request.query)
            # Feature hashing is an offline fallback rather than a semantic model. Over-fetch a
            # bounded set from Qdrant and use deterministic lexical reranking to reduce collisions.
            limit = (
                min(request.top_k * 20, 600)
                if self.embedder.identity.startswith("hash-")
                else request.top_k
            )
            primary = self.store.search(
                vector,
                limit=limit,
                filters=filters,
                embedding_id=self.embedder.identity,
            )
            # Product + exact version is often lost in a large hash index. Retrieve an
            # additional bounded set constrained by title terms, with the identical ACL.
            version = re.search(r"\b([A-Za-z][A-Za-z0-9-]*)\s+(\d+(?:\.\d+){1,4})\b",
                                request.query)
            if version and self.embedder.identity.startswith("hash-"):
                async def anchored() -> list[Document]:
                    try:
                        return await asyncio.wait_for(
                            self.store.search(
                                vector, limit=request.top_k * 4, filters=filters,
                                embedding_id=self.embedder.identity, title_query=version.group(),
                            ), timeout=min(self.timeout / 2, 10),
                        )
                    except Exception:
                        LOGGER.exception("Title retrieval failed; using dense candidates")
                        return []
                batches = await asyncio.gather(primary, anchored())
                return [document for batch in batches for document in batch]
            return await primary

        try:
            records = await asyncio.wait_for(search(), timeout=self.timeout)
            seen: set[str] = set()
            result: list[Document] = []
            for document in records:
                # Defense in depth: never trust an adapter to have enforced the ACL.
                if any(document.metadata.get(k) != v for k, v in filters.items()):
                    continue
                if document.chunk_id not in seen:
                    seen.add(document.chunk_id)
                    result.append(document)
            if self.embedder.identity.startswith("hash-"):
                query_terms = terms(request.query)

                def lexical_score(document: Document) -> tuple[float, float]:
                    title = str(document.metadata.get("title", ""))
                    document_terms = terms(document.text + " " + title)
                    coverage = len(query_terms & document_terms) / max(len(query_terms), 1)
                    return coverage, document.score

                result.sort(key=lexical_score, reverse=True)
            LOGGER.info("Retriever Tool returned %d candidates", min(len(result), request.top_k))
            return result[: request.top_k]
        except Exception as exc:
            LOGGER.exception("Retriever Tool timed out or failed")
            raise DependencyUnavailable("Knowledge-base retrieval unavailable") from exc
