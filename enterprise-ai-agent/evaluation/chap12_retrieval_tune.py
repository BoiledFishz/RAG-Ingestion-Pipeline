"""Retrieval design study on the disjoint TUNE split only (never on the evaluation sample).

    python -m evaluation.chap12_retrieval_tune --split tune
Reports document-level recall of the gold answer document for each retrieval variant,
using the exact SampleRetrieverTool the RAG Worker uses (offline lexical rerank).
"""

from __future__ import annotations

import argparse
import asyncio
import json
import math
import os
from pathlib import Path
from typing import Any

from rag.techqa.data import ROOT

from agents.chap12.rag_worker import doc_id
from models.schemas import RetrieverInput
from tools.sample_retriever import SampleRetrieverTool

HERE = Path(__file__).resolve().parent / "chap12"


def wilson(k: int, n: int) -> list[float]:
    z, p = 1.959964, k / n
    c = (p + z * z / (2 * n)) / (1 + z * z / n)
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return [round(c - h, 3), round(c + h, 3)]


async def evaluate(tool: SampleRetrieverTool, tasks: list[dict[str, Any]],
                   gold: dict[str, str], depth: int) -> dict[str, Any]:
    ranks: list[int | None] = []
    for task in tasks:
        docs = await tool.invoke(RetrieverInput(query=task["query"][:2000], top_k=depth))
        ids = list(dict.fromkeys(doc_id(d.chunk_id) for d in docs))
        target = gold[task["task_id"]]
        ranks.append(ids.index(target) + 1 if target in ids else None)
    n = len(ranks)
    out: dict[str, Any] = {"n": n}
    for k in (1, 3, 5, 8, 20):
        if k <= depth:
            hits = sum(1 for r in ranks if r and r <= k)
            out[f"R@{k}"] = {"value": round(hits / n, 3), "hits": hits, "wilson95": wilson(hits, n)}
    out["MRR"] = round(sum(1 / r for r in ranks if r) / n, 3)
    return out


async def calibrate(tool: SampleRetrieverTool, tasks: list[dict[str, Any]],
                    answerable: dict[str, bool]) -> dict[str, Any]:
    """Keep the reused Project 1 operating point: the highest top-1 rerank score threshold
    that still accepts at least the Project 1 hybrid answer-acceptance rate on tune Y.

    Maximizing balanced accuracy alone selects a degenerate threshold (accept ~14% of Y)
    because the score barely separates Y from N; that would turn the RAG Worker into a refuser.
    Labels come from the tune split only."""
    target = json.loads((ROOT / "config/techqa_thresholds.json").read_text(encoding="utf-8"))[
        "thresholds"]["hybrid_rerank"]["answer_acceptance"]
    top: list[tuple[float, bool]] = []
    for task in tasks:
        outcome = await tool.pipeline.retrieve(task["query"][:2000], mode=tool.mode)
        top.append((outcome.results[0].score if outcome.results else 0.0,
                    answerable[task["task_id"]]))
    ys = [s for s, y in top if y]
    ns = [s for s, y in top if not y]
    best: dict[str, Any] = {}
    for threshold in sorted({s for s, _ in top}):
        accepted = sum(s >= threshold for s in ys) / len(ys)
        refused = sum(s < threshold for s in ns) / len(ns)
        row = {"threshold": threshold, "balanced_accuracy": (accepted + refused) / 2,
               "answer_acceptance": accepted, "labelled_refusal": refused}
        if accepted >= target and (not best or threshold > best["threshold"]):
            best = row
    return {**{k: round(v, 4) for k, v in best.items()}, "y": len(ys), "n": len(ns),
            "target_answer_acceptance": round(target, 4)}


async def main_async(split: str, depth: int) -> None:
    # Recall ignores acceptance thresholds (they only annotate candidates); the threshold
    # itself is produced below by calibrate().
    os.environ.setdefault("CHAP12_MINILM_THRESHOLD", "0")
    folder = HERE if split == "sample" else HERE / split
    index = ROOT / f".rag_data/chap12_{split}.sqlite"
    tasks = [json.loads(x) for x in (folder / "tasks.jsonl").read_text(encoding="utf-8")
             .splitlines()]
    gold_rows = [json.loads(x) for x in (folder / "gold.jsonl").read_text(encoding="utf-8")
                 .splitlines()]
    gold = {g["task_id"]: g["document"] for g in gold_rows if g["answerable"] == "Y"}
    answerable = {g["task_id"]: g["answerable"] == "Y" for g in gold_rows}
    all_tasks = tasks
    tasks = [t for t in tasks if t["task_id"] in gold]
    hybrid_rrf = SampleRetrieverTool(index, semantic_rerank=False)
    hybrid_rrf.pipeline.reranker = None  # fused RRF order, no rerank
    dense_only = SampleRetrieverTool(index, semantic_rerank=False)
    dense_only.mode = "dense"
    minilm = SampleRetrieverTool(index, rerank="minilm")
    variants = {
        "sparse_bm25+lexical_rerank (v1)": SampleRetrieverTool(index, semantic_rerank=False,
                                                               use_dense=False),
        "hybrid+lexical_rerank": SampleRetrieverTool(index, semantic_rerank=False),
        "hybrid_rrf_no_rerank": hybrid_rrf,
        "dense_only": dense_only,
        "hybrid+minilm_rerank": minilm,
    }
    report: dict[str, Any] = {name: await evaluate(tool, tasks, gold, depth)
                              for name, tool in variants.items()}
    if split == "tune":
        thresholds = {"minilm_rerank": await calibrate(minilm, all_tasks, answerable),
                      "split": "tune",
                      "method": "highest top-1 threshold keeping Project 1 answer acceptance"}
        (folder / "thresholds.json").write_text(json.dumps(thresholds, indent=2) + "\n",
                                                encoding="utf-8")
        report["calibration"] = thresholds
    report["note"] = (f"split={split}; offline lexical rerank; doc-level gold recall over "
                      f"Y questions; depth={depth}")
    (folder / f"retrieval_report_{split}.json").write_text(
        json.dumps(report, indent=1) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=1))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--split", choices=["tune", "sample"], default="tune")
    parser.add_argument("--depth", type=int, default=20)
    args = parser.parse_args()
    asyncio.run(main_async(args.split, args.depth))


if __name__ == "__main__":
    main()
