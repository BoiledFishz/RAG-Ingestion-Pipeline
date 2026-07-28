"""Fault-isolated, hash-idempotent ingestion orchestration."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from rag.ingestion.chunking import RecursiveChunker
from rag.ingestion.models import Chunk, IngestionStats
from rag.ingestion.providers import EmbeddingProvider, ExtractiveSummaryProvider, SummaryProvider
from rag.ingestion.utils import DocumentParser
from rag.ingestion.vector_store import QdrantVectorStore

LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class IngestionConfig:
    request_concurrency: int = 8
    embedding_batch_size: int = 32
    upsert_batch_size: int = 128


class IngestionPipeline:
    def __init__(
        self,
        *,
        parser: DocumentParser,
        chunker: RecursiveChunker,
        summarizer: SummaryProvider,
        embedder: EmbeddingProvider,
        store: QdrantVectorStore,
        config: IngestionConfig | None = None,
    ) -> None:
        self.parser = parser
        self.chunker = chunker
        self.summarizer = summarizer
        self.embedder = embedder
        self.store = store
        self.config = config or IngestionConfig()
        self._fallback_summarizer = ExtractiveSummaryProvider()

    async def run(self, source: Path) -> IngestionStats:
        stats = IngestionStats()
        paths = self._discover_files(source)
        stats.files_seen = len(paths)
        if not paths:
            LOGGER.warning("No supported PDF or Markdown files found under %s", source)
            return stats

        candidates: list[Chunk] = []
        for path in paths:
            LOGGER.info("Processing file %s", path)
            try:
                pages = await self.parser.parse_file(path)
                if not pages:
                    stats.files_failed += 1
                    stats.warnings.append(f"No usable content: {path}")
                    continue
                chunks = self.chunker.split_pages(pages)
                if not chunks:
                    stats.files_failed += 1
                    stats.warnings.append(f"No chunks created: {path}")
                    continue
                stats.files_succeeded += 1
                stats.pages_parsed += len(pages)
                stats.chunks_created += len(chunks)
                candidates.extend(chunks)
                LOGGER.info(
                    "Parsed %s into %d page(s), %d chunk(s)",
                    path.name,
                    len(pages),
                    len(chunks),
                )
            except Exception:
                stats.files_failed += 1
                stats.warnings.append(f"Unhandled file error: {path}")
                LOGGER.exception("Skipping damaged file %s", path)

        unique: dict[str, Chunk] = {}
        for chunk in candidates:
            unique.setdefault(chunk.chunk_hash, chunk)
        in_run_duplicates = len(candidates) - len(unique)

        try:
            existing = await self.store.existing_hashes(list(unique))
        except Exception:
            LOGGER.exception("Failed to check existing chunk hashes; no embeddings were requested")
            stats.warnings.append("Vector store hash check failed")
            return stats

        pending = [chunk for digest, chunk in unique.items() if digest not in existing]
        stats.chunks_skipped = in_run_duplicates + len(existing.intersection(unique))
        if not pending:
            LOGGER.info(
                "All %d chunk(s) already exist; skipped summary and embedding calls",
                len(unique),
            )
            return stats

        enriched = await self._add_context_summaries(pending, stats)
        embedded = await self._embed_batches(enriched, stats)
        if not embedded:
            return stats

        vector_size = len(embedded[0][1])
        try:
            await self.store.ensure_collection(vector_size)
        except Exception:
            LOGGER.exception("Unable to prepare vector collection")
            stats.warnings.append("Vector collection preparation failed")
            return stats

        for start in range(0, len(embedded), self.config.upsert_batch_size):
            batch = embedded[start : start + self.config.upsert_batch_size]
            try:
                await self.store.upsert(
                    [item[0] for item in batch],
                    [item[1] for item in batch],
                )
                stats.chunks_upserted += len(batch)
            except Exception:
                stats.warnings.append(f"Upsert failed for batch starting at {start}")
                LOGGER.exception("Failed to upsert chunk batch starting at %d", start)

        LOGGER.info(
            "Ingestion complete: files=%d succeeded=%d failed=%d created=%d skipped=%d upserted=%d",
            stats.files_seen,
            stats.files_succeeded,
            stats.files_failed,
            stats.chunks_created,
            stats.chunks_skipped,
            stats.chunks_upserted,
        )
        return stats

    @staticmethod
    def _discover_files(source: Path) -> list[Path]:
        if source.is_file():
            return [source] if source.suffix.lower() in DocumentParser.SUPPORTED_SUFFIXES else []
        if not source.is_dir():
            return []
        return sorted(
            path
            for path in source.rglob("*")
            if path.is_file() and path.suffix.lower() in DocumentParser.SUPPORTED_SUFFIXES
        )

    async def _add_context_summaries(
        self, chunks: Sequence[Chunk], stats: IngestionStats
    ) -> list[Chunk]:
        semaphore = asyncio.Semaphore(self.config.request_concurrency)

        async def enrich(chunk: Chunk) -> Chunk:
            used_fallback = False
            try:
                async with semaphore:
                    summary = await self.summarizer.summarize(chunk.text)
            except Exception:
                used_fallback = True
                summary = await self._fallback_summarizer.summarize(chunk.text)
                LOGGER.warning(
                    "LLM summary failed for chunk %s; used extractive fallback",
                    chunk.chunk_hash,
                )
            metadata = {
                **chunk.metadata,
                "context_summary": summary,
                "summary_fallback": used_fallback,
            }
            return Chunk(text=chunk.text, metadata=metadata)

        enriched = await asyncio.gather(*(enrich(chunk) for chunk in chunks))
        fallback_count = sum(bool(chunk.metadata.get("summary_fallback")) for chunk in enriched)
        if fallback_count:
            stats.warnings.append(f"Used extractive summaries for {fallback_count} chunk(s)")
        return list(enriched)

    async def _embed_batches(
        self, chunks: Sequence[Chunk], stats: IngestionStats
    ) -> list[tuple[Chunk, list[float]]]:
        semaphore = asyncio.Semaphore(self.config.request_concurrency)
        batches = [
            list(chunks[start : start + self.config.embedding_batch_size])
            for start in range(0, len(chunks), self.config.embedding_batch_size)
        ]

        async def embed_batch(
            batch_number: int, batch: list[Chunk]
        ) -> list[tuple[Chunk, list[float]]]:
            try:
                async with semaphore:
                    vectors = await self.embedder.embed_documents([chunk.text for chunk in batch])
                if len(vectors) != len(batch):
                    raise ValueError("Embedding provider returned the wrong vector count")
                return list(zip(batch, vectors, strict=True))
            except Exception:
                stats.warnings.append(f"Embedding failed for batch {batch_number}")
                LOGGER.exception(
                    "Embedding batch %d failed; continuing with other batches", batch_number
                )
                return []

        nested = await asyncio.gather(
            *(embed_batch(number, batch) for number, batch in enumerate(batches, start=1))
        )
        flattened = [item for batch in nested for item in batch]
        dimensions = {len(vector) for _, vector in flattened}
        if len(dimensions) > 1:
            LOGGER.error(
                "Embedding provider returned inconsistent vector dimensions: %s", dimensions
            )
            stats.warnings.append("Inconsistent embedding dimensions")
            return []
        return flattened
