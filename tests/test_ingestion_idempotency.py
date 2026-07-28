from __future__ import annotations

import asyncio
from pathlib import Path

from rag.ingestion.chunking import RecursiveChunker
from rag.ingestion.models import Chunk
from rag.ingestion.pipeline import IngestionPipeline
from rag.ingestion.providers import ExtractiveSummaryProvider, HashEmbeddingProvider
from rag.ingestion.utils import DocumentParser


class CountingEmbedder(HashEmbeddingProvider):
    def __init__(self) -> None:
        super().__init__(dimensions=32)
        self.document_calls = 0

    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        self.document_calls += 1
        return await super().embed_documents(texts)


class MemoryStore:
    def __init__(self) -> None:
        self.hashes: set[str] = set()
        self.chunks: list[Chunk] = []

    async def existing_hashes(self, hashes: list[str]) -> set[str]:
        return self.hashes.intersection(hashes)

    async def ensure_collection(self, vector_size: int) -> None:
        assert vector_size > 0

    async def upsert(self, chunks: list[Chunk], vectors: list[list[float]]) -> None:
        self.chunks.extend(chunks)
        self.hashes.update(chunk.chunk_hash for chunk in chunks)


def test_second_ingestion_skips_embedding_and_preserves_required_metadata(tmp_path: Path) -> None:
    document = tmp_path / "guide.md"
    document.write_text(
        "# S3\nAn explicit deny overrides an allow in an S3 bucket policy.",
        encoding="utf-8",
    )
    store = MemoryStore()
    embedder = CountingEmbedder()
    pipeline = IngestionPipeline(
        parser=DocumentParser(),
        chunker=RecursiveChunker(chunk_size=256, chunk_overlap=32),
        summarizer=ExtractiveSummaryProvider(),
        embedder=embedder,
        store=store,  # type: ignore[arg-type]
    )

    first = asyncio.run(pipeline.run(tmp_path))
    second = asyncio.run(pipeline.run(tmp_path))

    assert first.chunks_upserted == 1
    assert second.chunks_upserted == 0
    assert second.chunks_skipped == 1
    assert embedder.document_calls == 1
    metadata = store.chunks[0].metadata
    assert {"source_file", "page_number", "chunk_hash", "context_summary"} <= metadata.keys()
