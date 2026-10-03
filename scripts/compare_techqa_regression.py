"""Compare recorded Agent runs on the unchanged official development regression questions."""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
from collections import Counter
from pathlib import Path
from typing import Any

from rag.techqa.data import FIXTURE_ROOT
from rag.techqa.metrics import body_token_f1

LOGGER = logging.getLogger(__name__)


def summarize(rows: list[dict[str, Any]], questions: dict[str, Any]) -> dict[str, Any]:
    positive = [r for r in rows if questions[r["question_id"]]["ANSWERABLE"] == "Y"]
    negative = [r for r in rows if questions[r["question_id"]]["ANSWERABLE"] == "N"]
    scores = []
    for row in positive:
        response = row.get("response") or {}
        expected = questions[row["question_id"]]
        answer = response.get("answer", "")
        cited = any(source["source_file"] == f"techqa://{expected['DOCUMENT']}"
                    and f"[{source['source_id']}]" in answer
                    for source in response.get("sources", []))
        scores.append(body_token_f1(answer, expected["ANSWER"]) * cited)
    return {
        "questions": len(rows), "answerable": len(positive), "labelled_N": len(negative),
        "execution_errors": sum(bool(r.get("error")) for r in rows),
        "statuses": dict(Counter((r.get("trace") or {}).get("status", "error") for r in rows)),
        "answerable_body_f1": sum(scores) / max(len(scores), 1),
        "answerable_acceptance": sum(bool((r.get("response") or {}).get("sources"))
                                     for r in positive) / max(len(positive), 1),
        "labelled_N_refusal_proxy": sum(not r.get("error") and (r.get("trace") or {}).get(
            "status") == "unanswerable" for r in negative) / max(len(negative), 1),
        "average_latency_ms": sum(r["latency_ms"] for r in rows) / max(len(rows), 1),
    }


def compare(baseline: Path, current: Path) -> dict[str, Any]:
    questions = {r["QUESTION_ID"]: r for r in json.loads(
        (FIXTURE_ROOT / "regression/questions.json").read_text(encoding="utf-8"),
    )}
    before_all = json.loads(baseline.read_text(encoding="utf-8"))
    before = [r for r in before_all if r["question_id"] in questions]
    after = json.loads(current.read_text(encoding="utf-8"))
    for rows in [before, after]:
        identifiers = [r["question_id"] for r in rows]
        if len(identifiers) != len(questions) or set(identifiers) != set(questions):
            raise ValueError("Each comparison must contain every original question exactly once")
    previous = {r["question_id"]: r for r in before}
    cases = []
    for row in after:
        identifier = row["question_id"]
        earlier = previous[identifier]
        cases.append({
            "question_id": identifier, "answerable_label": questions[identifier]["ANSWERABLE"],
            "before_status": earlier["trace"]["status"], "after_status": row["trace"]["status"],
            "before_body_f1": earlier["answer_quality"], "after_body_f1": row["answer_quality"],
            "before_sources": [s["source_file"] for s in earlier["response"]["sources"]],
            "after_sources": [s["source_file"] for s in row["response"]["sources"]],
            "validation_failures": row["trace"].get("validation_failures", []),
        })
    return {
        "protocol": "16 unchanged official TechQA development questions; fresh full-corpus "
        "semantic retrieval, query rewrite and native model execution after repairs",
        "baseline": {"path": str(baseline),
                     "sha256": hashlib.sha256(baseline.read_bytes()).hexdigest(),
                     "summary": summarize(before, questions)},
        "current": {"path": str(current),
                    "sha256": hashlib.sha256(current.read_bytes()).hexdigest(),
                    "summary": summarize(after, questions)},
        "cases": cases,
        "limitations": ["Development regression selected partly from known failures, not held-out",
                        "N labels concern original DOC_IDS, not absence from the full corpus",
                        "Body F1 and reference-document citations are proxies for answer quality",
                        "A safe refusal does not establish successful resolution",
                        "Shared desktop load makes latency comparisons non-isolated"],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--current", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = compare(args.baseline, args.current)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n",
                           encoding="utf-8")
    LOGGER.info("Development regression comparison: %s", result["current"]["summary"])


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
