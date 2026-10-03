"""Reproduce or verify the development regression snapshot against original TechQA."""

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path
from typing import Any

from rag.techqa.data import ARCHIVE_SHA256, FIXTURE_ROOT, digest, documents, questions

LOGGER = logging.getLogger(__name__)
FAILURES = {"DEV_Q000", "DEV_Q007", "DEV_Q113", "DEV_Q236"}


def original_snapshot() -> dict[str, Any]:
    original = questions("dev")
    ordered_controls = [row["QUESTION_ID"] for row in original
                        if row["QUESTION_ID"] not in FAILURES][:12]
    selected = [row for row in original
                if row["QUESTION_ID"] in FAILURES or row["QUESTION_ID"] in ordered_controls]
    wanted = {row["DOCUMENT"] for row in selected if row["ANSWERABLE"] == "Y"}
    wanted.update({"swg21960632", "swg21679259", "swg21970417", "swg21681385"})
    docs = [doc for doc in documents("core") if doc["id"] in wanted]
    if {doc["id"] for doc in docs} != wanted:
        raise ValueError("Missing original TechQA regression document")
    return {"questions": selected, "documents": docs, "manifest": {
        "dataset": "IBM TechQA", "upstream": "https://github.com/ibm/techqa",
        "archive_sha256": ARCHIVE_SHA256, "question_split": "dev",
        "selection": "DEV_Q000, DEV_Q007, DEV_Q113, DEV_Q236 plus the first 12 other "
        "official dev records in original order",
        "purpose": "development regression, not held-out evaluation; native runs retrieve "
        "the full 801996-document corpus",
        "questions": len(selected), "documents": len(docs),
        "content_hashes": {doc["id"]: digest(doc["text"]) for doc in docs},
    }}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true", help="Recreate the original-text snapshots")
    parser.add_argument("--output", type=Path, help="Save verification evidence as JSON")
    args = parser.parse_args()
    folder = FIXTURE_ROOT / "regression"
    snapshot = original_snapshot()
    if args.write:
        folder.mkdir(parents=True, exist_ok=True)
        for name, value in snapshot.items():
            (folder / f"{name}.json").write_text(
                json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8",
            )
    for name, expected in snapshot.items():
        actual = json.loads((folder / f"{name}.json").read_text(encoding="utf-8"))
        if actual != expected:
            raise ValueError(f"Regression {name} differs from original official TechQA records")
    result = {"verified": True, "archive_sha256": ARCHIVE_SHA256,
              "questions": len(snapshot["questions"]), "documents": len(snapshot["documents"]),
              "question_ids": [row["QUESTION_ID"] for row in snapshot["questions"]],
              "source": "Official dev_Q_A.json and training_dev_technotes.json",
              "scope": "Development regression; not held-out evaluation"}
    if args.output:
        args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    LOGGER.info("Original TechQA regression snapshot verified: %s", result)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
