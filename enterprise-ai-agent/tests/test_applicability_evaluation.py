import asyncio
import json

from rag.techqa.data import documents, questions

from evaluation import review_applicability
from models.schemas import Evidence


def test_reviewer_outages_remain_failures_and_never_earn_refusal_credit(monkeypatch, tmp_path):
    original = questions("fixture")
    rows = [original[0], next(r for r in original if r["ANSWERABLE"] == "N")]
    doc = next(d for d in documents("fixture") if d["id"] == rows[0]["DOCUMENT"])
    evidence = Evidence(source_id="S1", chunk_id=f"techqa:{doc['id']}:parent",
                        source_file=f"techqa://{doc['id']}", page_number=1,
                        excerpt=doc["text"], relevance=1, tokens=100)
    question_path = tmp_path / "questions.json"
    question_path.write_text(json.dumps(rows), encoding="utf-8")
    monkeypatch.setattr(review_applicability, "DEV_PATH", question_path)
    monkeypatch.setattr(review_applicability, "checkpoint_protocol", lambda *_: {})
    baseline = [{
        "question_id": row["QUESTION_ID"], "answerable": row["ANSWERABLE"] == "Y",
        "error": None, "answer_quality": 0,
        "trace": {"status": "answered", "evidence": [evidence.model_dump()]},
        "response": {"answer": doc["text"] + " [S1]", "confidence": 0.8, "sources": [{
            "source_id": "S1", "chunk_id": evidence.chunk_id,
            "source_file": evidence.source_file, "page_number": 1, "quote": doc["text"],
        }]},
    } for row in rows]
    source = tmp_path / "baseline.json"
    source.write_text(json.dumps(baseline), encoding="utf-8")

    class Unavailable:
        async def generate(self, prompt, schema):
            raise TimeoutError("Injected model outage")

    monkeypatch.setattr(review_applicability, "OllamaStructuredModel", lambda *_: Unavailable())
    summary = asyncio.run(review_applicability.evaluate(source, tmp_path / "results"))
    assert summary["complete"] and summary["questions"] == 2
    assert summary["error_count"] == 2
    assert summary["review_rejected_count"] == 0
    assert summary["reviewed_labelled_refusal_accuracy"] == 0
    assert summary["reviewed_answerable_body_f1"] == 0
