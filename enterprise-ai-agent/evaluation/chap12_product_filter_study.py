"""P1-5 alternative: resolve the product slot first, then use it for BOTH DB and RAG filtering.

    python -m evaluation.chap12_product_filter_study            # tune split (design)
Compares, on Y questions, gold-document recall of RAG retrieval without a product filter
(current design) vs. restricted to the resolved product (literal, else inferred), and the
added latency of resolving the slot before retrieval (which makes RAG wait for it).
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import statistics
import time
from pathlib import Path
from typing import Any

from rag.techqa.data import ROOT

from agents.chap12.contracts import TrustedContext
from agents.chap12.db_worker import DatabaseQueryWorker
from agents.chap12.rag_worker import doc_id
from agents.chap12.scope import product_scope
from models.schemas import RetrieverInput
from tools.sample_retriever import SampleRetrieverTool

HERE = Path(__file__).resolve().parent / "chap12"


def recall(ranks: list[int | None]) -> dict[str, float]:
    n = len(ranks)
    out = {f"R@{k}": round(sum(1 for r in ranks if r and r <= k) / n, 4) for k in (1, 3, 5, 8)}
    out["MRR"] = round(sum(1 / r for r in ranks if r) / n, 4)
    return out


async def main_async(split: str) -> None:
    os.environ.setdefault("CHAP12_MINILM_THRESHOLD", "0")
    os.environ.setdefault("CHAP12_GAP_GATE", "")  # recall study: gate off
    folder = HERE if split == "sample" else HERE / split
    index = ROOT / f".rag_data/chap12_{split}.sqlite"
    tasks = [json.loads(x) for x in (folder / "tasks.jsonl").read_text("utf-8").splitlines()]
    gold = {g["task_id"]: g for g in map(json.loads,
                                         (folder / "gold.jsonl").read_text("utf-8").splitlines())}
    tasks = [t for t in tasks if gold[t["task_id"]]["answerable"] == "Y"]
    tool = SampleRetrieverTool(index, rerank="minilm")
    worker = DatabaseQueryWorker(index)
    full = TrustedContext.model_validate({
        "subject_id": "study", "tenant_id": "course", "allowed_workers": ["rag", "database"],
        "allowed_db_operations": ["count_documents"], "allowed_product_ids": ["*"]})
    plain: list[int | None] = []
    filtered: list[int | None] = []
    resolve_ms: list[float] = []
    resolved = 0
    for task in tasks:
        query, target = task["query"][:2000], gold[task["task_id"]]["document"]
        docs = await tool.invoke(RetrieverInput(query=query, top_k=8))
        ids = [doc_id(d.chunk_id) for d in docs]
        plain.append(ids.index(target) + 1 if target in ids else None)
        started = time.monotonic()
        found = worker.catalog.find(query)
        product: str | None
        if found:
            product = found[0].product_id
        else:
            product = (await asyncio.to_thread(worker._infer, query, full))[0]
        resolve_ms.append((time.monotonic() - started) * 1000)
        if product is None:
            filtered.append(plain[-1])  # no slot: falls back to unfiltered retrieval
            continue
        resolved += 1
        with product_scope(frozenset({product})):
            docs = await tool.invoke(RetrieverInput(query=query, top_k=8))
        ids = [doc_id(d.chunk_id) for d in docs]
        filtered.append(ids.index(target) + 1 if target in ids else None)
    report: dict[str, Any] = {
        "split": split, "y_questions": len(tasks), "slot_resolved": resolved,
        "unfiltered_parallel (current)": recall(plain),
        "product_filtered_serial (alternative)": recall(filtered),
        "slot_resolution_ms": {"mean": round(statistics.fmean(resolve_ms), 1),
                               "p95": round(sorted(resolve_ms)[int(0.95 * len(resolve_ms))], 1)},
        "note": "Filtered retrieval must wait for slot resolution (serial); unfiltered RAG runs "
                "in parallel with DB. Unresolved questions fall back to unfiltered retrieval.",
    }
    (folder / "product_filter_study.json").write_text(json.dumps(report, indent=1) + "\n",
                                                      "utf-8")
    print(json.dumps(report, indent=1))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--split", choices=["tune"], default="tune")
    asyncio.run(main_async(parser.parse_args().split))


if __name__ == "__main__":
    main()
