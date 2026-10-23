"""Build the Chap12 random sample: 100-200 official training questions + candidate documents.

Usage (from enterprise-ai-agent, PYTHONPATH=../src;.):
    python -m evaluation.chap12_build_sample --size 150 --seed 20261011

Outputs (all new paths; existing outputs are never overwritten):
    ../.rag_data/chap12_sample.sqlite     documents, FTS index, structured technotes table
    evaluation/chap12/tasks.jsonl         task_id, question_id, query (no answers/labels)
    evaluation/chap12/gold.jsonl          answers/labels/gold doc for offline scoring only
    evaluation/chap12/sample_manifest.json
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from rag.techqa.data import DATA_ROOT, INDEX_PATH, ROOT, question_text

from agents.chap12.sample import (
    DEFAULT_SEED,
    DEFAULT_SIZE,
    SAMPLE_SCOPE,
    candidate_doc_ids,
    docs_from_full_index,
    select_questions,
    sha256_file,
    write_index,
)

AGENT_ROOT = Path(__file__).resolve().parents[1]
SAMPLE_INDEX = ROOT / ".rag_data/chap12_sample.sqlite"
OUTPUT = AGENT_ROOT / "evaluation/chap12"


def relative(path: Path) -> str:
    resolved, root = path.resolve(), ROOT.resolve()
    return resolved.relative_to(root).as_posix() if resolved.is_relative_to(root) else str(path)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--size", type=int, default=DEFAULT_SIZE)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--index", type=Path, default=SAMPLE_INDEX)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    parser.add_argument("--full-index", type=Path, default=INDEX_PATH)
    parser.add_argument("--exclude-manifest", type=Path, nargs="*", default=[],
                        help="sample_manifest.json whose questions must not be reused "
                             "(builds a disjoint tune split)")
    args = parser.parse_args()

    source = DATA_ROOT / "training_and_dev/training_Q_A.json"
    pool = json.loads(source.read_text(encoding="utf-8"))
    excluded: set[str] = set()
    for manifest_path in args.exclude_manifest:
        excluded |= set(json.loads(manifest_path.read_text(encoding="utf-8"))["question_ids"])
    pool = [q for q in pool if q["QUESTION_ID"] not in excluded]
    questions = select_questions(pool, args.size, args.seed)
    doc_ids = candidate_doc_ids(questions)
    for path in (args.output / "tasks.jsonl", args.output / "gold.jsonl"):
        if path.exists():
            raise FileExistsError(f"{path} exists; samples are immutable")
    count = write_index(
        args.index,
        docs_from_full_index(args.full_index, doc_ids),
        {"seed": str(args.seed), "questions": str(len(questions)),
         "source_split": "training_Q_A.json", "source_sha256": sha256_file(source)},
    )
    gold_ids = {str(q["DOCUMENT"]) for q in questions if q["ANSWERABLE"] == "Y"}
    args.output.mkdir(parents=True, exist_ok=True)
    with (args.output / "tasks.jsonl").open("x", encoding="utf-8") as tasks, \
            (args.output / "gold.jsonl").open("x", encoding="utf-8") as gold:
        for number, q in enumerate(questions, 1):
            task = {"task_id": f"C12-{number:03d}", "question_id": q["QUESTION_ID"],
                    "query": question_text(q), "goal": "explain_and_data"}
            tasks.write(json.dumps(task, ensure_ascii=False) + "\n")
            gold.write(json.dumps({
                "task_id": task["task_id"], "question_id": q["QUESTION_ID"],
                "answerable": q["ANSWERABLE"], "document": q["DOCUMENT"], "answer": q["ANSWER"],
            }, ensure_ascii=False) + "\n")
    manifest = {
        "scope": SAMPLE_SCOPE, "seed": args.seed, "size": len(questions),
        "source_split": "training_Q_A.json (official TechQA training; dev/held-out untouched)",
        "source_sha256": sha256_file(source),
        "answerable": sum(q["ANSWERABLE"] == "Y" for q in questions),
        "unanswerable": sum(q["ANSWERABLE"] == "N" for q in questions),
        "candidate_doc_ids": len(doc_ids), "indexed_documents": count,
        "missing_documents": len(doc_ids) - count,
        "gold_documents_indexed": len(gold_ids),
        "excluded_questions": len(excluded),
        "question_ids": [q["QUESTION_ID"] for q in questions],
        "index_path": relative(args.index), "index_sha256": sha256_file(args.index),
        "note": ("Retrieval thresholds of the reused Project 1 pipeline were calibrated on the "
                 "training split; absolute RAG metrics are optimistic, comparisons share them."),
    }
    (args.output / "sample_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in manifest.items() if k != "question_ids"}, indent=2))


if __name__ == "__main__":
    main()
