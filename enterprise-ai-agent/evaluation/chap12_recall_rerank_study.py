"""Offline study of the two remaining loss layers (2026-10-24; diagnosis only, no model calls).

    python -m evaluation.chap12_recall_rerank_study --cache PATH/techqa_rerank_cache.sqlite

Uses the layer trace of the current configuration on the TUNE split
(results/chap12/tune_real_r9_base, Ollama 0.40.9) and the sample index:
  recall  rebuild the fused candidates offline (BM25 + the sample MiniLM vectors) for the
          rewritten query that was actually used and for the original question; the rebuilt
          rewritten@30 list must equal the traced fusion. Count answerable questions whose gold
          document is among the candidates for: rewritten@30 (current), rewritten@50,
          original@30, and RRF-merged rewritten+original cut at 30 / 40 / 50.
  rerank  (a) union: how many gold documents are in "rerank top 8 + fusion top k" (k = 2, 3, 4)
          versus rerank top 8, and how many documents that adds; (b) decomposition: recompute
          the Project 1 rerank score (0.5 semantic + 0.3 lexical + 0.2 BM25 prior) from the
          cached nomic vectors (read-only; a missing vector is an error), check it reproduces
          the traced rerank order, and for questions whose gold document was pushed out of the
          top 8 compare its three components with the 8th document's; (c) counterfactual
          orderings of the same candidates for every answerable question (gold in top 8):
          current weights; prior from the fused (RRF) rank instead of the BM25 rank, so that
          dense-only hits are not scored as BM25 rank 1000; and the semantic/lexical/prior
          weights 0.7/0.3/0 and 0.6/0.3/0.1; each at candidate_k 30 and 50.
Writes results/chap12/recall_rerank_study.json. Nothing here selects a parameter; it only
decides what a later pre-registered run should try.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import sqlite3
from dataclasses import replace
from pathlib import Path
from statistics import mean
from typing import Any

from rag.techqa.data import ROOT

HERE = Path(__file__).resolve().parent
RUN = HERE / "results/chap12/tune_real_r9_base"
VARIANTS = {  # semantic, lexical, prior weights; prior from fused rank?
    "current": (0.5, 0.3, 0.2, False),
    "fused_prior": (0.5, 0.3, 0.2, True),
    "w70_30_0": (0.7, 0.3, 0.0, False),
    "w60_30_10": (0.6, 0.3, 0.1, False),
}


class CachedOnlyReranker:
    """Project 1 TechQAReranker with embeddings served only from an existing cache."""

    def __init__(self, cache: Path) -> None:
        from rag.techqa.retrieval import TechQAReranker

        self.inner = TechQAReranker(semantic=True)
        self.db = sqlite3.connect(f"file:{cache}?mode=ro", uri=True)
        model = self.inner.embedder.model
        db = self.db

        async def embeddings(texts: list[str]) -> list[list[float]]:
            out = []
            for t in texts:
                key = hashlib.sha256((model + ":v1:" + t).encode()).hexdigest()
                row = db.execute("SELECT vector FROM embeddings WHERE key=?", (key,)).fetchone()
                if row is None:
                    raise KeyError("nomic vector not cached")
                out.append(json.loads(row[0]))
            return out

        self.inner.embeddings = embeddings  # type: ignore[method-assign]


def variant_score(x: dict[str, float], fused_rank: int,
                  variant: tuple[float, float, float, bool]) -> float:
    ws, wl, wp, use_fused = variant
    prior = 1 / (1 + fused_rank / 5) if use_fused else x["bm25_prior"]
    return ws * x["semantic_score"] + wl * x["lexical_score"] + wp * prior


def doc_rank(results: list[Any]) -> list[str]:
    from agents.chap12.rag_worker import doc_id

    out: list[str] = []
    for r in results:
        d = doc_id(str(r.metadata.get("parent_id", "")))
        if d not in out:
            out.append(d)
    return out


def rrf(lists: list[list[Any]], k: int = 60) -> list[Any]:
    scores: dict[str, float] = {}
    keep: dict[str, Any] = {}
    for results in lists:
        for rank, r in enumerate(results, 1):
            key = str(r.metadata.get("chunk_id") or r.text[:80])
            scores[key] = scores.get(key, 0.0) + 1 / (k + rank)
            keep.setdefault(key, r)
    return [keep[key] for key in sorted(scores, key=lambda key: -scores[key])]


async def main_async(args: argparse.Namespace) -> None:
    from tools.sample_retriever import SampleRetrieverTool

    tool = SampleRetrieverTool(ROOT / ".rag_data/chap12_tune.sqlite", rerank="lexical")
    base_config = tool.pipeline.config
    reranker = CachedOnlyReranker(args.cache)
    tasks = {t["task_id"]: t for t in map(json.loads, (HERE / "chap12/tune/mixed_tasks.jsonl")
                                          .read_text("utf-8").splitlines())}
    gold = {g["task_id"]: g for g in map(json.loads, (HERE / "chap12/tune/mixed_gold.jsonl")
                                         .read_text("utf-8").splitlines())}
    rows = [json.loads(x) for x in (RUN / "traces.jsonl").read_text("utf-8-sig").splitlines()
            if x.strip()]
    rows = [r for r in rows if r["score"].get("answerable") and r["layers"].get("retrieval")]

    async def fused(query: str, k: int) -> list[Any]:
        tool.pipeline.config = replace(base_config, candidate_k=k)
        stages: dict[str, Any] = {}
        await tool.pipeline.retrieve(query, mode=tool.mode, filters=tool.secure_filters({}),
                                     trace=stages)
        tool.pipeline.config = base_config
        return list(stages["fusion"])

    recall = {name: 0 for name in ("rewritten@30", "rewritten@50", "original@30",
                                   "merged@30", "merged@40", "merged@50")}
    union = {f"rerank8+fusion{k}": {"gold": 0, "added_docs": []} for k in (2, 3, 4)}
    union["rerank8"] = {"gold": 0, "added_docs": []}
    pushed: list[dict[str, Any]] = []
    counter: dict[str, int] = {}
    unavailable: dict[str, int] = {}
    mismatch_fusion = mismatch_rerank = missing_vectors = 0
    for r in rows:
        g = gold[r["task_id"]]["document"]
        stages = r["layers"]["retrieval"]["stages"]
        rw, orig = r["layers"]["retrieval"]["query"], tasks[r["task_id"]]["query"]
        rw30, rw50 = await fused(rw, 30), await fused(rw, 50)
        or30, or50 = await fused(orig, 30), await fused(orig, 50)
        if doc_rank(rw30) != [x["doc"] for x in stages["fusion"]]:
            mismatch_fusion += 1
        lists = {"rewritten@30": rw30, "rewritten@50": rw50, "original@30": or30}
        merged = rrf([rw50, or50])
        for k in (30, 40, 50):
            lists[f"merged@{k}"] = merged[:k]
        for name, results in lists.items():
            recall[name] += g in doc_rank(results)
        rerank_docs = [x["doc"] for x in stages["rerank"]]
        fusion_docs = [x["doc"] for x in stages["fusion"]]
        top8 = rerank_docs[:8]
        union["rerank8"]["gold"] += g in top8
        for k in (2, 3, 4):
            extra = [d for d in fusion_docs[:k] if d not in top8]
            union[f"rerank8+fusion{k}"]["gold"] += g in top8 + extra
            union[f"rerank8+fusion{k}"]["added_docs"].append(len(extra))
        for k_name, cands in (("30", rw30), ("50", rw50)):
            comps: dict[str, dict[str, float]] = {}
            try:
                await reranker.inner.rerank(rw, cands, limit=len(cands), components=comps)
            except KeyError:  # candidates beyond 30 were never embedded in the real runs
                unavailable[k_name] = unavailable.get(k_name, 0) + 1
                continue
            fused_rank = {c.chunk_id: i for i, c in enumerate(cands, 1)}
            for name, variant in VARIANTS.items():
                order = doc_rank(sorted(cands, key=lambda c, v=variant: variant_score(
                    comps[c.chunk_id], fused_rank[c.chunk_id], v), reverse=True))
                key = f"{name}@{k_name}"
                counter[key] = counter.get(key, 0) + (g in order[:8])
        if g in fusion_docs and g not in top8:
            components: dict[str, dict[str, float]] = {}
            try:
                ranked = await reranker.inner.rerank(rw, rw30, limit=len(rw30),
                                                     components=components)
            except KeyError:
                missing_vectors += 1
                continue
            order = doc_rank(ranked)
            if order[:len(rerank_docs)] != rerank_docs:
                mismatch_rerank += 1
            by_doc: dict[str, dict[str, float]] = {}
            for res in ranked:
                d = doc_rank([res])[0]
                by_doc.setdefault(d, components[res.chunk_id])
            eighth = order[7] if len(order) >= 8 else order[-1]
            pushed.append({"task_id": r["task_id"], "gold_rank_fusion": fusion_docs.index(g) + 1,
                           "gold_rank_rerank": order.index(g) + 1,
                           "gold": by_doc[g], "eighth": by_doc[eighth]})
    gaps = {c: round(mean(p["eighth"][c] - p["gold"][c] for p in pushed), 4)
            for c in ("semantic_score", "lexical_score", "bm25_prior")} if pushed else {}
    weighted = {c: round(w * gaps.get(c, 0.0), 4) for c, w in (
        ("semantic_score", 0.5), ("lexical_score", 0.3), ("bm25_prior", 0.2))}
    out = {"run": str(RUN), "answerable_tasks": len(rows),
           "fusion_rebuild_mismatches": mismatch_fusion,
           "rerank_rebuild_mismatches": mismatch_rerank, "missing_vectors": missing_vectors,
           "recall_gold_in_candidates": recall,
           "counterfactual_gold_in_top8": counter,
           "counterfactual_unavailable_tasks": unavailable,
           "union": {k: {"gold_in_list": v["gold"],
                         "mean_added_docs": round(mean(v["added_docs"]), 2) if v["added_docs"]
                         else 0.0} for k, v in union.items()},
           "pushed_out_of_top8": {"count": len(pushed),
                                  "mean_gap_8th_minus_gold": gaps,
                                  "weighted_gap": weighted, "items": pushed}}
    (HERE / "results/chap12/recall_rerank_study.json").write_text(
        json.dumps(out, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in out.items() if k != "pushed_out_of_top8"}, indent=1))
    print(json.dumps({k: v for k, v in out["pushed_out_of_top8"].items() if k != "items"},
                     indent=1))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cache", type=Path, required=True)
    asyncio.run(main_async(parser.parse_args()))


if __name__ == "__main__":
    main()
