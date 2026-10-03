"""Reproduce relevance thresholds using only a completed official training run."""

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path
from typing import Any

from rag.techqa.data import ROOT

LOGGER = logging.getLogger(__name__)


def calibrate(directory: Path) -> dict[str, Any]:
    summary = json.loads((directory / "summary.json").read_text(encoding="utf-8"))
    rows = [
        json.loads(line)
        for line in (directory / "runs.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    if summary["split"] != "train" or any(not r["id"].startswith("TRAIN_") for r in rows):
        raise ValueError("Calibration requires official training questions, never dev/validation")
    if len(rows) != summary["questions"] or any(r["error"] for r in rows):
        raise ValueError("Calibration requires a complete run without retrieval errors")
    positive = [r for r in rows if r["answerable"]]
    negative = [r for r in rows if not r["answerable"]]
    if not positive or not negative:
        raise ValueError("Calibration requires both answerable and unanswerable labels")
    result: dict[str, Any] = {
        "split": f"first {len(rows)} official training questions",
        "count": len(rows),
        "answerable_count": len(positive),
        "unanswerable_count": len(negative),
        "protocol": "open-corpus proxy; N labels only assert no answer in official DOC_IDS",
        "model": "nomic-embed-text",
        "candidate_k": 30,
        "thresholds": {},
    }
    for mode in ("dense_rerank", "hybrid_rerank"):
        scores = sorted({float(r["modes"][mode]["top_score"] or 0) for r in rows})
        candidates = [
            0.0,
            *((lower + upper) / 2 for lower, upper in zip(scores[:-1], scores[1:], strict=True)),
            scores[-1] + 1e-9,
        ]
        options = []
        for threshold in candidates:
            accepted = sum(
                float(r["modes"][mode]["top_score"] or 0) >= threshold for r in positive
            ) / len(positive)
            refused = sum(
                float(r["modes"][mode]["top_score"] or 0) < threshold for r in negative
            ) / len(negative)
            options.append({
                "threshold": threshold,
                "balanced_accuracy": (accepted + refused) / 2,
                "answer_acceptance": accepted,
                "labelled_refusal": refused,
            })
        # Prefer acceptance if balanced accuracy ties; all candidates use train labels only.
        result["thresholds"][mode] = max(
            options, key=lambda row: (row["balanced_accuracy"], row["answer_acceptance"])
        )
    if all("expected_document" in row for row in rows):
        result["dense_embedding"] = summary["dense_embedding"]
        result["evaluation_directory"] = directory.resolve().relative_to(ROOT).as_posix()
        supported_scores: list[float] = []
        for row in positive:
            mode = row["modes"]["hybrid_rerank"]
            supported_scores.extend(
                score for doc_id, score in zip(
                    mode["document_ids"], mode["candidate_scores"], strict=True
                ) if doc_id == row["expected_document"]
            )
        if not supported_scores:
            raise ValueError("No known relevant training candidates for evidence selection")
        supported_scores.sort()
        # Keep all observed relevant training candidates; the LLM still must
        # establish answer sufficiency. This is distinct from automatic answer acceptance.
        threshold = supported_scores[0]
        result["evidence_candidate_threshold"] = {
            "threshold": threshold,
            "relevant_training_candidates": len(supported_scores),
            "conditional_retention": sum(s >= threshold for s in supported_scores)
            / len(supported_scores),
            "method": "minimum observed relevant train Top-10 candidate score; "
            "not answer confidence",
        }
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=ROOT / "evals/techqa_semantic_calibration")
    parser.add_argument("--output", type=Path, default=ROOT / "config/techqa_thresholds.json")
    args = parser.parse_args()
    result = calibrate(args.input)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    LOGGER.info("Training-only thresholds written to %s", args.output)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
