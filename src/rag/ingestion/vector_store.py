"""Qdrant persistence with hash-first idempotency checks."""

from __future__ import annotations

import asyncio
import logging
import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from rag.ingestion.models import Chunk, MetadataValue

LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class VectorRecord:
    text: str
    metadata: dict[str, MetadataValue]
    score: float = 0.0


class QdrantVectorStore:
    """Local or remote Qdrant adapter used by ingestion and retrieval."""

    def __init__(
        self,
        *,
        collection_name: str = "aws_support",
        path: Path | None = Path(".rag_data/qdrant"),
        url: str | None = None,
        api_key: str | None = None,
    ) -> None:
        from qdrant_client import QdrantClient

        if url:
            self._client = QdrantClient(url=url, api_key=api_key)
        elif path is not None:
            path.parent.mkdir(parents=True, exist_ok=True)
            self._client = QdrantClient(path=str(path))
        else:
            self._client = QdrantClient(":memory:")
        self.collection_name = collection_name

    async def collection_exists(self) -> bool:
        return await asyncio.to_thread(self._client.collection_exists, self.collection_name)

    async def ensure_collection(self, vector_size: int) -> None:
        await asyncio.to_thread(self._ensure_collection_sync, vector_size)

    def _ensure_collection_sync(self, vector_size: int) -> None:
        from qdrant_client.models import Distance, VectorParams

        if self._client.collection_exists(self.collection_name):
            info = self._client.get_collection(self.collection_name)
            vectors = info.config.params.vectors
            existing_size = getattr(vectors, "size", None)
            if existing_size is not None and int(existing_size) != vector_size:
                raise ValueError(
                    f"Collection {self.collection_name!r} expects vectors of size "
                    f"{existing_size}, received {vector_size}"
                )
            return
        self._client.create_collection(
            collection_name=self.collection_name,
            vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE),
        )
        LOGGER.info(
            "Created Qdrant collection %s (dimension=%d)",
            self.collection_name,
            vector_size,
        )

    async def existing_hashes(self, hashes: Sequence[str]) -> set[str]:
        if not hashes or not await self.collection_exists():
            return set()
        return await asyncio.to_thread(self._existing_hashes_sync, list(dict.fromkeys(hashes)))

    def _existing_hashes_sync(self, hashes: list[str]) -> set[str]:
        from qdrant_client.models import FieldCondition, Filter, MatchAny

        found: set[str] = set()
        for start in range(0, len(hashes), 256):
            batch = hashes[start : start + 256]
            points, _ = self._client.scroll(
                collection_name=self.collection_name,
                scroll_filter=Filter(
                    must=[FieldCondition(key="chunk_hash", match=MatchAny(any=batch))]
                ),
                limit=len(batch),
                with_payload=["chunk_hash"],
                with_vectors=False,
            )
            for point in points:
                if point.payload and point.payload.get("chunk_hash"):
                    found.add(str(point.payload["chunk_hash"]))
        return found

    async def upsert(self, chunks: Sequence[Chunk], vectors: Sequence[Sequence[float]]) -> None:
        if len(chunks) != len(vectors):
            raise ValueError("chunks and vectors must have equal lengths")
        if not chunks:
            return
        await asyncio.to_thread(self._upsert_sync, list(chunks), list(vectors))

    def _upsert_sync(self, chunks: list[Chunk], vectors: list[Sequence[float]]) -> None:
        from qdrant_client.models import PointStruct

        points = []
        for chunk, vector in zip(chunks, vectors, strict=True):
            point_id = str(uuid.uuid5(uuid.NAMESPACE_URL, chunk.chunk_hash))
            payload: dict[str, Any] = {"text": chunk.text, **chunk.metadata}
            points.append(PointStruct(id=point_id, vector=list(vector), payload=payload))
        self._client.upsert(collection_name=self.collection_name, points=points, wait=True)

    async def search(
        self,
        vector: Sequence[float],
        *,
        limit: int = 10,
        filters: dict[str, MetadataValue] | None = None,
    ) -> list[VectorRecord]:
        if not await self.collection_exists():
            return []
        return await asyncio.to_thread(self._search_sync, list(vector), limit, filters)

    def _search_sync(
        self,
        vector: list[float],
        limit: int,
        filters: dict[str, MetadataValue] | None,
    ) -> list[VectorRecord]:
        from qdrant_client.models import FieldCondition, Filter, MatchValue

        query_filter = None
        if filters:
            query_filter = Filter(
                must=[
                    FieldCondition(key=key, match=MatchValue(value=value))
                    for key, value in filters.items()
                ]
            )
        response = self._client.query_points(
            collection_name=self.collection_name,
            query=vector,
            query_filter=query_filter,
            limit=limit,
            with_payload=True,
            with_vectors=False,
        )
        records: list[VectorRecord] = []
        for point in response.points:
            payload = dict(point.payload or {})
            text = str(payload.pop("text", ""))
            metadata = {
                key: value
                for key, value in payload.items()
                if isinstance(value, (str, int, float, bool))
            }
            records.append(VectorRecord(text=text, metadata=metadata, score=float(point.score)))
        return records

    async def list_records(self) -> list[VectorRecord]:
        if not await self.collection_exists():
            return []
        return await asyncio.to_thread(self._list_records_sync)

    def _list_records_sync(self) -> list[VectorRecord]:
        records: list[VectorRecord] = []
        offset: Any = None
        while True:
            points, offset = self._client.scroll(
                collection_name=self.collection_name,
                offset=offset,
                limit=256,
                with_payload=True,
                with_vectors=False,
            )
            for point in points:
                payload = dict(point.payload or {})
                text = str(payload.pop("text", ""))
                metadata = {
                    key: value
                    for key, value in payload.items()
                    if isinstance(value, (str, int, float, bool))
                }
                records.append(VectorRecord(text=text, metadata=metadata))
            if offset is None:
                break
        return records
