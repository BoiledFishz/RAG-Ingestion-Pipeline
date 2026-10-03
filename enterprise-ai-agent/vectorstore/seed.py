"""Download and idempotently index the official IBM TechQA dataset."""

from __future__ import annotations

import argparse
import asyncio
import logging
from typing import Literal, cast

from agents.rag_agent.factory import build_embedder, open_store
from models.settings import Settings
from vectorstore.techqa import (
    ARCHIVE_DEFAULT,
    EXTRACTED_DEFAULT,
    ChunkingConfig,
    batched,
    chunks_from_documents,
    document_stream,
    download_archive,
    extract_archive,
)

LOGGER = logging.getLogger(__name__)


async def ingest(
    scope: Literal["core", "full"], chunk_size: int, overlap: int, batch_size: int
) -> None:
    settings = Settings.from_env()
    if not settings.collection.startswith("techqa_"):
        raise ValueError("TechQA ingestion requires a techqa_* collection")
    archive = download_archive(ARCHIVE_DEFAULT)
    root = extract_archive(archive, EXTRACTED_DEFAULT, scope=scope)
    store = open_store(settings.model_copy(update={"retrieval_backend": "legacy"}))
    assert store is not None
    indexed = seen = 0
    try:
        embedder = build_embedder(settings)
        chunks = chunks_from_documents(
            document_stream(root, scope), ChunkingConfig(chunk_size, overlap)
        )
        for batch in batched(chunks, batch_size):
            indexed += await store.seed(batch, embedder)
            seen += len(batch)
            if seen % (batch_size * 20) == 0:
                LOGGER.info(
                    "TechQA progress: chunks_seen=%d newly_indexed=%d", seen, indexed
                )
    finally:
        await store.close()
    LOGGER.info(
        "TechQA ingestion complete: scope=%s chunks_seen=%d newly_indexed=%d",
        scope,
        seen,
        indexed,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scope", choices=("core", "full"), default="full")
    parser.add_argument("--chunk-size", type=int, default=1200)
    parser.add_argument("--chunk-overlap", type=int, default=160)
    parser.add_argument("--batch-size", type=int, default=128)
    args = parser.parse_args()
    scope = cast(Literal["core", "full"], args.scope)
    asyncio.run(ingest(scope, args.chunk_size, args.chunk_overlap, args.batch_size))


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")
    logging.getLogger("httpx").setLevel(logging.WARNING)
    main()
