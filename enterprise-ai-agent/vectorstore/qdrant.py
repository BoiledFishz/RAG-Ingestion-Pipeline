"""Bounded vector search; seeding is explicit and never runs during queries."""

from __future__ import annotations

import asyncio
import hashlib
import logging
import uuid
from collections.abc import Sequence
from pathlib import Path
from typing import Any, Protocol

from models.providers import Embedder
from models.schemas import Document, MetadataValue

LOGGER = logging.getLogger(__name__)


class VectorStore(Protocol):
    async def search(
        self,
        vector: list[float],
        *,
        limit: int,
        filters: dict[str, MetadataValue],
        embedding_id: str,
        title_query: str | None = None,
    ) -> list[Document]: ...


class QdrantStore:
    def __init__(
        self,
        collection: str,
        *,
        path: Path | None = None,
        url: str | None = None,
        api_key: str | None = None,
    ) -> None:
        from qdrant_client import QdrantClient

        self.collection = collection
        if url:
            self.client = QdrantClient(
                url=url,
                api_key=api_key,
                timeout=30,
                # REST avoids observed protobuf response decoding failures on Windows/Python 3.14.
                prefer_grpc=False,
            )
        elif path is not None:
            path.parent.mkdir(parents=True, exist_ok=True)
            self.client = QdrantClient(path=str(path))
        else:
            self.client = QdrantClient(":memory:")

    async def close(self) -> None:
        await asyncio.to_thread(self.client.close)

    async def search(
        self,
        vector: list[float],
        *,
        limit: int,
        filters: dict[str, MetadataValue],
        embedding_id: str,
        title_query: str | None = None,
    ) -> list[Document]:
        return await asyncio.to_thread(
            self._search, vector, limit, filters, embedding_id, title_query,
        )

    def _search(
        self,
        vector: list[float],
        limit: int,
        filters: dict[str, MetadataValue],
        embedding_id: str,
        title_query: str | None = None,
    ) -> list[Document]:
        from qdrant_client.models import FieldCondition, Filter, MatchText, MatchValue

        if not self.client.collection_exists(self.collection):
            raise ValueError("Collection missing; run python -m vectorstore.seed first")
        info = self.client.get_collection(self.collection)
        size = getattr(info.config.params.vectors, "size", None)
        if size != len(vector):
            raise ValueError("Embedding dimension does not match the indexed documents")
        conditions = [
            FieldCondition(key=key, match=MatchValue(value=value))
            for key, value in filters.items()
        ]
        if title_query:
            conditions.append(FieldCondition(key="title", match=MatchText(text=title_query)))
        points = self.client.query_points(
            collection_name=self.collection,
            query=vector,
            limit=limit,
            query_filter=Filter(must=conditions),
            with_payload=True,
            with_vectors=False,
        ).points
        documents = []
        for point in points:
            payload = dict(point.payload or {})
            if payload.get("_embedding_id") not in (None, embedding_id):
                raise ValueError("Embedding model identity mismatch")
            text = str(payload.pop("text", ""))
            if not text.strip():
                continue
            metadata = {k: v for k, v in payload.items() if isinstance(v, (str, int, float, bool))}
            documents.append(
                Document(
                    chunk_id=str(payload.get("chunk_id") or payload.get("chunk_hash") or point.id),
                    text=text,
                    source_file=str(payload.get("source_file", "unknown")),
                    page_number=payload.get("page_number", 1),
                    score=float(point.score),
                    metadata=metadata,
                )
            )
        return documents

    async def seed(self, documents: Sequence[Document], embedder: Embedder) -> int:
        """Hash-first idempotency; skip embedding charges for previously seeded points."""
        if not documents:
            return 0
        exists = await asyncio.to_thread(self.client.collection_exists, self.collection)
        identifiers = [
            str(uuid.uuid5(uuid.NAMESPACE_URL, hashlib.sha256(d.text.encode()).hexdigest()))
            for d in documents
        ]
        existing: dict[str, Any] = {}
        if exists:
            records = await asyncio.to_thread(
                self.client.retrieve,
                self.collection,
                identifiers,
                with_payload=True,
                with_vectors=False,
            )
            existing = {str(p.id): p.payload or {} for p in records}
            if any(p.get("_embedding_id") != embedder.identity for p in existing.values()):
                raise ValueError("Do not seed different embeddings into an existing collection")
        missing = [
            (d, key) for d, key in zip(documents, identifiers, strict=True) if key not in existing
        ]
        if not missing:
            LOGGER.info("Seed skipped: all %d chunks already indexed", len(documents))
            return 0
        vectors = await embedder.embed_documents([d.text for d, _ in missing])
        if len(vectors) != len(missing):
            raise ValueError("Embedding count mismatch")
        await asyncio.to_thread(self._write, missing, vectors, embedder.identity, exists)
        LOGGER.info("Seeded %d chunks into %s", len(missing), self.collection)
        return len(missing)

    def _write(
        self,
        documents: list[tuple[Document, str]],
        vectors: list[list[float]],
        identity: str,
        exists: bool,
    ) -> None:
        from qdrant_client.models import Distance, PointStruct, VectorParams

        if not exists:
            self.client.create_collection(
                self.collection,
                vectors_config=VectorParams(
                    size=len(vectors[0]),
                    distance=Distance.COSINE,
                ),
            )
        else:
            info = self.client.get_collection(self.collection)
            if getattr(info.config.params.vectors, "size", None) != len(vectors[0]):
                raise ValueError("Embedding dimension mismatch; choose another collection")
        self.client.upsert(
            self.collection,
            points=[
                PointStruct(
                    id=key,
                    vector=vector,
                    payload={
                        **doc.metadata,
                        "text": doc.text,
                        "chunk_id": doc.chunk_id,
                        "chunk_hash": hashlib.sha256(doc.text.encode()).hexdigest(),
                        "source_file": doc.source_file,
                        "page_number": doc.page_number,
                        "_embedding_id": identity,
                    },
                )
                for (doc, key), vector in zip(documents, vectors, strict=True)
            ],
            wait=True,
        )
