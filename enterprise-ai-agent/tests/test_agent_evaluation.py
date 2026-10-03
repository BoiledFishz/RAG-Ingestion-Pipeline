from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest
from rag.techqa.data import questions

from evaluation import evaluate as benchmark
from evaluation.evaluate import hit_at_k, question_text, reciprocal_rank
from models.settings import Settings
from tools.retriever import RetrieverTool
from vectorstore.qdrant import QdrantStore


def test_hit_and_mrr_formulas() -> None:
    assert hit_at_k(["techqa:a:0:x", "techqa:b:0:y"], {"b"}, 1) == 0
    assert hit_at_k(["techqa:a:0:x", "techqa:b:0:y"], {"b"}, 2) == 1
    assert reciprocal_rank(["techqa:a:0:x", "techqa:b:0:y"], {"b"}) == 0.5


def test_official_question_fields_and_missing_body() -> None:
    assert question_text({"QUESTION_TITLE": "Title", "QUESTION_TEXT": "Body"}) == "Title\nBody"
    assert question_text({"QUESTION_TITLE": "Title", "QUESTION_BODY": "Body"}) == "Title\nBody"
    assert question_text({"QUESTION_TITLE": "Title", "QUESTION_TEXT": "Title"}) == "Title"
    assert question_text({"QUESTION_TITLE": "Title"}) == "Title"


def test_failed_questions_remain_in_evaluation_denominators(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    dataset = tmp_path / "dev.json"
    dataset.write_text(
        json.dumps([
            questions("fixture")[0],
            next(q for q in questions("fixture") if q["ANSWERABLE"] == "N"),
        ])
    )

    async def fail(*args, **kwargs):
        raise TimeoutError("Injected dependency error")

    monkeypatch.setattr(RetrieverTool, "invoke", fail)
    monkeypatch.setattr(benchmark, "open_store", lambda _: QdrantStore("errors"))
    result = asyncio.run(benchmark.evaluate(Settings(retrieval_backend="legacy"), dataset))
    summary = result["summary"]
    assert summary["question_count"] == 2
    assert summary["answerable_count"] == summary["unanswerable_count"] == 1
    assert summary["error_count"] == 2
    assert summary["hit_at_5"] == summary["unanswerable_refusal_accuracy"] == 0


def test_resume_retries_failures_without_replaying_successes_or_mixing_models(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    dataset = tmp_path / "dev.json"
    dataset.write_text(json.dumps([
        questions("fixture")[0],
        next(q for q in questions("fixture") if q["ANSWERABLE"] == "N"),
    ]))
    calls = []

    async def invoke(self, request):
        calls.append(request.query)
        if len(calls) == 2:
            raise TimeoutError("One transient failure")
        return []

    monkeypatch.setattr(RetrieverTool, "invoke", invoke)
    monkeypatch.setattr(benchmark, "open_store", lambda _: QdrantStore("resume"))
    settings = Settings(retrieval_backend="legacy")
    output = tmp_path / "checkpoint"
    first = asyncio.run(benchmark.evaluate(settings, dataset, output))
    assert first["summary"]["error_count"] == 1
    second = asyncio.run(benchmark.evaluate(settings, dataset, output, resume=True))
    assert len(calls) == 3
    assert second["summary"]["question_count"] == 2
    assert second["summary"]["error_count"] == 0
    assert second["summary"]["reused_questions"] == 1
    assert len((output / "progress.jsonl").read_text(encoding="utf-8").splitlines()) == 3
    with pytest.raises(ValueError, match="configuration changed"):
        asyncio.run(benchmark.evaluate(
            settings.model_copy(update={"model": "changed-model"}), dataset, output, resume=True,
        ))
