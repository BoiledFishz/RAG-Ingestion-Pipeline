"""Command-line entry point for ingestion."""

from __future__ import annotations

import argparse
import asyncio
import logging
import os
from collections.abc import Sequence
from pathlib import Path

from rag.ingestion.chunking import RecursiveChunker
from rag.ingestion.pipeline import IngestionConfig, IngestionPipeline
from rag.ingestion.providers import (
    EmbeddingProvider,
    ExtractiveSummaryProvider,
    HashEmbeddingProvider,
    OllamaEmbeddingProvider,
    OllamaSummaryProvider,
    SummaryProvider,
)
from rag.ingestion.utils import DocumentParser
from rag.ingestion.vector_store import QdrantVectorStore

LOGGER = logging.getLogger(__name__)


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Ingest PDF/Markdown documents into Qdrant")
    parser.add_argument("source", type=Path, help="Document file or directory")
    parser.add_argument(
        "--qdrant-path",
        type=Path,
        default=Path(os.getenv("QDRANT_PATH", ".rag_data/qdrant")),
    )
    parser.add_argument("--collection", default=os.getenv("QDRANT_COLLECTION", "aws_support"))
    parser.add_argument("--chunk-size", type=int, default=int(os.getenv("CHUNK_SIZE", "512")))
    parser.add_argument("--chunk-overlap", type=int, default=int(os.getenv("CHUNK_OVERLAP", "64")))
    parser.add_argument(
        "--summary-provider",
        choices=("ollama", "extractive"),
        default=os.getenv("SUMMARY_PROVIDER", "ollama"),
    )
    parser.add_argument(
        "--embedding-provider",
        choices=("ollama", "hash"),
        default=os.getenv("EMBEDDING_PROVIDER", "ollama"),
    )
    parser.add_argument(
        "--concurrency",
        type=int,
        default=int(os.getenv("REQUEST_CONCURRENCY", "8")),
    )
    parser.add_argument("--log-level", default=os.getenv("LOG_LEVEL", "INFO"))
    return parser


async def async_run(arguments: argparse.Namespace) -> int:
    ollama_base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    summarizer: SummaryProvider
    if arguments.summary_provider == "ollama":
        summarizer = OllamaSummaryProvider(
            model=os.getenv("SUMMARY_MODEL", "llama3.2:3b"), base_url=ollama_base_url
        )
    else:
        summarizer = ExtractiveSummaryProvider()

    embedder: EmbeddingProvider
    if arguments.embedding_provider == "ollama":
        embedder = OllamaEmbeddingProvider(
            model=os.getenv("EMBEDDING_MODEL", "nomic-embed-text"),
            base_url=ollama_base_url,
            batch_size=int(os.getenv("EMBEDDING_BATCH_SIZE", "32")),
            concurrency=arguments.concurrency,
        )
    else:
        embedder = HashEmbeddingProvider()

    parser = DocumentParser(
        ocr_languages=os.getenv("OCR_LANGUAGES", "eng"),
        tesseract_cmd=os.getenv("TESSERACT_CMD") or None,
    )
    pipeline = IngestionPipeline(
        parser=parser,
        chunker=RecursiveChunker(
            chunk_size=arguments.chunk_size, chunk_overlap=arguments.chunk_overlap
        ),
        summarizer=summarizer,
        embedder=embedder,
        store=QdrantVectorStore(path=arguments.qdrant_path, collection_name=arguments.collection),
        config=IngestionConfig(request_concurrency=arguments.concurrency),
    )
    stats = await pipeline.run(arguments.source)
    return 1 if stats.files_seen and stats.files_succeeded == 0 else 0


def run(argv: Sequence[str] | None = None) -> int:
    arguments = build_argument_parser().parse_args(argv)
    logging.basicConfig(
        level=getattr(logging, str(arguments.log_level).upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
    )
    try:
        return asyncio.run(async_run(arguments))
    except KeyboardInterrupt:
        LOGGER.warning("Ingestion interrupted")
        return 130
    except Exception:
        LOGGER.exception("Fatal pipeline configuration error")
        return 1
