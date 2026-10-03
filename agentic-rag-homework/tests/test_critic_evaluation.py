"""A missing retrieved context must never look like a successful model review."""

import asyncio

from rag.techqa.data import questions

from evaluation import critic_stability


def test_empty_retrieval_records_all_trials_without_model_calls(monkeypatch, tmp_path):
    official = questions("fixture")
    rows = [official[0], next(row for row in official if row["ANSWERABLE"] == "N")]
    monkeypatch.setattr(critic_stability, "questions", lambda _: rows)

    class EmptyStore:
        async def search(self, query, top_k):
            return []

    def forbidden_model(**kwargs):
        raise AssertionError("No evidence must bypass the model")

    monkeypatch.setattr(critic_stability, "TechQAStore", EmptyStore)
    monkeypatch.setattr(critic_stability, "OllamaStructuredModel", forbidden_model)
    summary = asyncio.run(critic_stability.evaluate(
        2, 2, tmp_path, False, "retrieved", "fixture", "all",
    ))
    assert summary["complete"]
    assert summary["trials"] == 4
    assert summary["model_trials"] == 0
    assert summary["skipped_no_evidence"] == 4
    assert summary["skipped_answerable_trials"] == 2
    assert summary["pass_rate"] == 0
    assert summary["sufficiency_consistency"] == 0
    assert summary["labelled_refusal_accuracy"] == 0
    assert len((tmp_path / "runs.jsonl").read_text(encoding="utf-8").splitlines()) == 4
