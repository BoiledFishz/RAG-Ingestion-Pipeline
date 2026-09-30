from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from rag.ingestion.cli import async_run, build_argument_parser
from rag.ingestion.providers import HashEmbeddingProvider, OllamaSummaryProvider, _first_sentence


def test_embedding_failure_is_nonzero_and_database_is_released(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = tmp_path / "document.md"
    source.write_text("An explicit deny overrides an allow in an S3 bucket policy.")
    arguments = build_argument_parser().parse_args([
        str(source), "--summary-provider", "extractive", "--embedding-provider", "hash",
        "--qdrant-path", str(tmp_path / "db"),
    ])

    async def unavailable(self: HashEmbeddingProvider, texts: list[str]) -> list[list[float]]:
        raise RuntimeError("embedding offline")

    with monkeypatch.context() as context:
        context.setattr(HashEmbeddingProvider, "embed_documents", unavailable)
        assert asyncio.run(async_run(arguments)) == 1
    # A later retry must be able to open the same DB, write data and then skip it.
    assert asyncio.run(async_run(arguments)) == 0
    assert asyncio.run(async_run(arguments)) == 0


def test_missing_input_is_not_reported_as_success(tmp_path: Path) -> None:
    args = build_argument_parser().parse_args([
        str(tmp_path / "missing"), "--summary-provider", "extractive",
        "--embedding-provider", "hash", "--qdrant-path", str(tmp_path / "db"),
    ])
    assert asyncio.run(async_run(args)) == 1


def test_summary_keeps_complete_sentence_and_version_number() -> None:
    sentence = "Version 4.1.1.2 requires " + "a documented condition, " * 12 + "not a restart."
    assert _first_sentence(sentence + " A second unrelated sentence.") == sentence


def test_token_truncated_summary_triggers_pipeline_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def truncated(self, endpoint, payload):
        return {"response": "The bucket requires an incom", "done_reason": "length"}

    monkeypatch.setattr(OllamaSummaryProvider, "_post_with_retry", truncated)
    with pytest.raises(ValueError, match="token-truncated"):
        asyncio.run(OllamaSummaryProvider().summarize("Complete original source sentence."))
