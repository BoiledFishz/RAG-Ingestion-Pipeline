"""Items 7 and 8 design study on the TUNE split only (seed 20261012 index, tasks seed 20261022).

    python -m evaluation.chap12_product_study

For the tune explain_and_data tasks it measures, without any model call:
* product resolution of the current rule (catalogue literal, else BM25 top-3 >= 60%);
* for unresolved tasks, how often the gold document's product is among the candidate products
  offered to a model-based catalogue pick (products of the top-N BM25 documents, at most
  MAX_CANDIDATES). This is an upper bound for the pick, not its accuracy;
* related-document variants for resolved products: the most recent documents (current) versus
  the product's own documents ranked by BM25 against the question.
Only the tune split is accepted. Output: evaluation/chap12/tune/product_study.json.

    python -m evaluation.chap12_product_study --pick      (needs Ollama; real model calls)

With --pick it also runs the real model pick on every answerable tune question (explain and
explain_and_data) whose text names no catalogue product, and chooses the order by a rule fixed
before the run:
"first" (model before rule) only if its gold-product match rate is at least 0.05 above
"fallback" (rule first, model only when the rule finds nothing); otherwise "fallback".
Output: evaluation/chap12/tune/product_pick.json (read by agents.chap12.product_pick).
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sqlite3
from collections import Counter
from pathlib import Path
from typing import Any

from rag.techqa.data import ROOT

from agents.chap12.contracts import TrustedContext
from agents.chap12.db_worker import DatabaseQueryWorker

HERE = Path(__file__).resolve().parent / "chap12" / "tune"
DEPTHS = (5, 10, 20)
MAX_CANDIDATES = 8
RELATED_K = 5


def products_of(db: sqlite3.Connection, doc: str) -> set[str]:
    return {r[0] for r in db.execute(
        "SELECT product_id FROM document_products WHERE doc_id = ?", (doc,))}


def candidates(worker: DatabaseQueryWorker, db: sqlite3.Connection, query: str,
               depth: int) -> list[str]:
    counts: Counter[str] = Counter()
    first: dict[str, int] = {}
    for rank, hit in enumerate(worker.index.search(query, depth)):
        for pid in products_of(db, hit["id"]):
            counts[pid] += 1
            first.setdefault(pid, rank)
    ranked = sorted(counts, key=lambda p: (-counts[p], first[p], p))
    return ranked[:MAX_CANDIDATES]


def related_bm25(worker: DatabaseQueryWorker, db: sqlite3.Connection, query: str,
                 product: str, k: int = RELATED_K, overfetch: int = 200) -> list[str]:
    out = []
    for hit in worker.index.search(query, overfetch):
        if product in products_of(db, hit["id"]):
            out.append(hit["id"])
            if len(out) == k:
                break
    return out


def related_recent(db: sqlite3.Connection, product: str, k: int = RELATED_K) -> list[str]:
    return [r[0] for r in db.execute(
        "SELECT DISTINCT t.doc_id FROM technotes t JOIN document_products p ON p.doc_id=t.doc_id "
        "WHERE p.product_id=? ORDER BY t.published_date DESC, t.doc_id LIMIT ?", (product, k))]


def rate(k: int, n: int) -> dict[str, Any]:
    return {"value": round(k / n, 3) if n else None, "hits": k, "n": n}


async def pick_study(worker: DatabaseQueryWorker, ctx: TrustedContext,
                     rows: list[dict[str, Any]], queries: dict[str, str]) -> dict[str, Any]:
    from agents.chap12.budget import Budget, BudgetedModel, metered
    from agents.chap12.factory import budget_limits
    from agents.chap12.ollama_tokens import TokenMeteredOllamaModel
    from agents.chap12.product_pick import ProductPicker
    from models.settings import Settings

    settings = Settings.from_env()
    picker = ProductPicker(BudgetedModel(TokenMeteredOllamaModel(
        settings.ollama_url, settings.model, settings.llm_timeout)))
    scored = []
    for row in rows:
        if row["answerable"] != "Y" or row["source"] == "literal":
            continue
        query = queries[row["task_id"]]
        ranked, _ = worker._candidates(query, ctx)
        options = [(p, worker.catalog.by_id[p].name) for p in ranked if p in worker.catalog.by_id]
        budget = Budget(budget_limits())  # one request budget per question, as in serving
        with metered(budget, "database"):
            try:
                # Bounded per call so one stuck request cannot stall the whole study.
                picked = await asyncio.wait_for(picker.pick(query, options), timeout=90)
            except TimeoutError:
                picker.errors += 1
                picked = None
        print(f"pick {len(scored) + 1}: {row['task_id']} -> {picked}", flush=True)
        inferred = row["product"]  # rule result (None when unresolved)
        target = set(row["gold_products"])
        scored.append({"task_id": row["task_id"], "inferred": inferred, "picked": picked,
                       "first": picked or inferred, "fallback": inferred or picked,
                       "gold_products": sorted(target)})
    n = len(scored)
    def hits(key: str) -> int:
        return sum(1 for r in scored if r[key] and r[key] in r["gold_products"])
    first, fallback = rate(hits("first"), n), rate(hits("fallback"), n)
    adopted = "first" if n and (hits("first") - hits("fallback")) / n >= 0.05 else "fallback"
    return {"split": "tune", "model": settings.model, "n_no_literal_y": n,
            "rule_alone": rate(hits("inferred"), n), "pick_alone": rate(hits("picked"), n),
            "first": first, "fallback": fallback, "model_errors": picker.errors,
            "rule": "first only if match(first) - match(fallback) >= 0.05",
            "adopted_mode": adopted, "rows": scored}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pick", action="store_true", help="run the real model pick study")
    args = parser.parse_args()
    index = ROOT / ".rag_data/chap12_tune.sqlite"
    worker = DatabaseQueryWorker(index)
    ctx = TrustedContext.model_validate({
        "subject_id": "study", "tenant_id": "course", "allowed_workers": {"database"},
        "allowed_db_operations": {"list_recent_documents"}, "allowed_product_ids": {"*"}})
    tasks = [json.loads(x) for x in (HERE / "mixed_tasks.jsonl").read_text("utf-8").splitlines()]
    gold = {g["task_id"]: g for g in map(
        json.loads, (HERE / "mixed_gold.jsonl").read_text("utf-8").splitlines())}
    db = sqlite3.connect(index.resolve().as_uri() + "?mode=ro", uri=True)
    rows = []
    # The pick study uses every tune question (resolution does not depend on the goal).
    kinds = {"explain", "explain_and_data"} if args.pick else {"explain_and_data"}
    for task in (t for t in tasks if t["type"] in kinds):
        g = gold[task["task_id"]]
        query = task["query"]
        found = worker.catalog.find(query)
        source, product = ("literal", found[0].product_id) if found else ("none", None)
        if product is None:
            inferred, _ = worker._infer(query, ctx)
            if inferred is not None:
                source, product = "inferred", inferred
        row: dict[str, Any] = {"task_id": task["task_id"], "answerable": g["answerable"],
                               "source": source, "product": product}
        if g["answerable"] == "Y":
            target = products_of(db, g["document"])
            row["gold_products"] = sorted(target)
            row["match"] = product in target if product else None
            for depth in DEPTHS:
                row[f"cand@{depth}"] = bool(target & set(candidates(worker, db, query, depth)))
            if product:
                row["related_recent"] = g["document"] in related_recent(db, product)
                row["related_bm25"] = g["document"] in related_bm25(worker, db, query, product)
        rows.append(row)
    y = [r for r in rows if r["answerable"] == "Y"]
    resolved = [r for r in y if r["product"]]
    unresolved = [r for r in y if not r["product"]]
    mismatched = [r for r in resolved if not r["match"]]
    summary = {
        "split": "tune", "index": index.name, "tasks": "tune/mixed_tasks.jsonl (seed 20261022)",
        "explain_and_data": len(rows), "answerable_y": len(y),
        "resolution": dict(Counter(r["source"] for r in rows)),
        "y_resolved": rate(len(resolved), len(y)),
        "y_resolved_matches_gold_doc": rate(sum(1 for r in resolved if r["match"]),
                                            len(resolved)),
        "pick_candidate_coverage_unresolved": {
            f"top{d}": rate(sum(1 for r in unresolved if r[f"cand@{d}"]), len(unresolved))
            for d in DEPTHS},
        "pick_candidate_coverage_mismatched": {
            f"top{d}": rate(sum(1 for r in mismatched if r[f"cand@{d}"]), len(mismatched))
            for d in DEPTHS},
        "related_contains_gold_resolved": {
            "recent": rate(sum(1 for r in resolved if r["related_recent"]), len(resolved)),
            "bm25_in_product": rate(sum(1 for r in resolved if r["related_bm25"]),
                                    len(resolved))},
        "max_candidates": MAX_CANDIDATES, "related_k": RELATED_K,
    }
    if args.pick:
        queries = {t["task_id"]: t["query"] for t in tasks}
        pick = asyncio.run(pick_study(worker, ctx, rows, queries))
        (HERE / "product_pick.json").write_text(json.dumps(pick, ensure_ascii=False, indent=1),
                                                encoding="utf-8")
        print(json.dumps({k: v for k, v in pick.items() if k != "rows"}, indent=1))
        return
    out = HERE / "product_study.json"
    out.write_text(json.dumps({"summary": summary, "rows": rows}, ensure_ascii=False, indent=1),
                   encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
