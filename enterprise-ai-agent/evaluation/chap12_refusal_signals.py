"""Refusal-signal study (decision D2) on the TUNE split only.

    python -m evaluation.chap12_refusal_signals
For each candidate signal, sweeps every observed threshold and reports Y acceptance,
N refusal and balanced accuracy (BA). Rule fixed before looking at results: a signal is
adopted only if its best tune BA exceeds 0.6; otherwise "no effective signal" is recorded.
Best-threshold BA is an in-sample (optimistic) figure.
"""

from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path
from typing import Any

from rag.techqa.data import ROOT
from rag.techqa.query import protected_terms
from rag.techqa.retrieval import coverage

from agents.chap12.db_worker import DatabaseQueryWorker
from agents.chap12.rag_worker import doc_id
from tools.sample_retriever import SampleRetrieverTool

HERE = Path(__file__).resolve().parent / "chap12"
ADOPTION_BA = 0.6


def curve(values: list[tuple[float, bool]]) -> list[dict[str, float]]:
    """Accept when value >= threshold."""
    ys = [v for v, y in values if y]
    ns = [v for v, y in values if not y]
    rows = []
    for threshold in sorted({v for v, _ in values}):
        accept = sum(v >= threshold for v in ys) / len(ys)
        refuse = sum(v < threshold for v in ns) / len(ns)
        rows.append({"threshold": round(threshold, 4), "y_accept": round(accept, 4),
                     "n_refuse": round(refuse, 4), "ba": round((accept + refuse) / 2, 4)})
    return rows


def auc(values: list[tuple[float, bool]]) -> float:
    ys = [v for v, y in values if y]
    ns = [v for v, y in values if not y]
    wins = sum((y > n) + 0.5 * (y == n) for y in ys for n in ns)
    return wins / (len(ys) * len(ns))


async def main_async(split: str) -> None:
    os.environ.setdefault("CHAP12_MINILM_THRESHOLD", "0")  # annotation only
    folder = HERE if split == "sample" else HERE / split
    index = ROOT / f".rag_data/chap12_{split}.sqlite"
    tasks = [json.loads(x) for x in (folder / "tasks.jsonl").read_text("utf-8").splitlines()]
    gold = {g["task_id"]: g for g in map(json.loads,
                                         (folder / "gold.jsonl").read_text("utf-8").splitlines())}
    tool = SampleRetrieverTool(index, rerank="minilm")
    worker = DatabaseQueryWorker(index)
    signals: dict[str, list[tuple[float, bool]]] = {
        "top1_rerank_score": [], "top1_top2_gap": [], "key_term_coverage_top1": [],
        "max_term_coverage_top3": [], "product_consistency_top3": []}
    no_literal = 0
    for task in tasks:
        query = task["query"][:2000]
        answerable = gold[task["task_id"]]["answerable"] == "Y"
        outcome = await tool.pipeline.retrieve(query, mode=tool.mode)
        results = outcome.results
        scores = [r.score for r in results] + [0.0, 0.0]
        signals["top1_rerank_score"].append((scores[0], answerable))
        signals["top1_top2_gap"].append((scores[0] - scores[1], answerable))
        texts = [r.text for r in results[:3]]
        terms = protected_terms(query)
        top1 = (texts[0] if texts else "").casefold()
        signals["key_term_coverage_top1"].append(
            (sum(t in top1 for t in terms) / len(terms) if terms else 0.0, answerable))
        signals["max_term_coverage_top3"].append(
            (max((coverage(query, t) for t in texts), default=0.0), answerable))
        literal = {p.product_id for p in worker.catalog.find(query)}
        if literal:
            docs = [doc_id(str(r.metadata.get("parent_id", ""))) for r in results[:3]]
            share = sum(bool(tool.scope.products.get(d, frozenset()) & literal)
                        for d in docs) / max(len(docs), 1)
            signals["product_consistency_top3"].append((share, answerable))
        else:
            no_literal += 1
    report: dict[str, Any] = {"split": split, "rule": f"adopt only if best BA > {ADOPTION_BA}",
                              "retrieval": "hybrid BM25+MiniLM, MiniLM rerank (final config)"}
    for name, values in signals.items():
        rows = curve(values)
        best = max(rows, key=lambda r: (r["ba"], r["y_accept"]))
        report[name] = {
            "n": len(values), "y": sum(y for _, y in values),
            "n_count": sum(not y for _, y in values),
            "auc": round(auc(values), 4), "best": best,
            "adopt": best["ba"] > ADOPTION_BA,
            "curve": rows if name == "top1_rerank_score" else None,
        }
    report["product_consistency_top3"]["excluded_no_literal_product"] = no_literal
    report["conclusion"] = (
        "no effective refusal signal (all best BA <= 0.6)"
        if not any(isinstance(v, dict) and v.get("adopt") for v in report.values())
        else "see adopt flags")
    (folder / "refusal_signals.json").write_text(json.dumps(report, indent=1) + "\n", "utf-8")
    for name in signals:
        r = report[name]
        print(name, "n", r["n"], "AUC", r["auc"], "best", r["best"], "adopt", r["adopt"])
    print(report["conclusion"])


def main() -> None:
    asyncio.run(main_async("tune"))


if __name__ == "__main__":
    main()

