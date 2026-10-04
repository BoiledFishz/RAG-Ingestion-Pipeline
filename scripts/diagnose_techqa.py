"""Read-only stage diagnostics and frozen-parent experiments on original TechQA.

Reference document IDs are used only AFTER open retrieval, in diagnostic scoring.
Neither IDs nor reference answers are passed to any retriever or model.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import logging
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx

from rag.retrieval.contracts import SearchResult
from rag.retrieval.fusion import reciprocal_rank_fusion
from rag.techqa.data import ROOT, question_text, questions
from rag.techqa.evidence import answer_passages
from rag.techqa.retrieval import TechQAReranker, build_pipeline, open_index

LOGGER = logging.getLogger(__name__)
CASES = ["DEV_Q000", "DEV_Q007", "TRAIN_Q006", "TRAIN_Q007", "TRAIN_Q011"]
CONTROLS = ["DEV_Q002", "DEV_Q010", "DEV_Q012", "TRAIN_Q000", "TRAIN_Q001"]
WEIGHTS = {"A": (0.50, 0.30, 0.20), "B": (0.60, 0.40, 0.0),
           "C": (0.70, 0.20, 0.10), "D": (1.0, 0.0, 0.0), "E": (0.0, 0.55, 0.45)}


def serialize(result: SearchResult) -> dict[str, Any]:
    return {**result.to_dict(), "score": result.score}


def target(rows: list[SearchResult], document_id: str) -> dict[str, Any]:
    hits = [(rank, row) for rank, row in enumerate(rows, 1)
            if row.metadata.get("techqa_document_id") == document_id]
    if not hits:
        return {"rank": None, "score": None, "chunk": None}
    rank, row = hits[0]
    return {"rank": rank, "score": row.score, "chunk": serialize(row)}


async def experiment(output: Path) -> None:
    await asyncio.to_thread(output.mkdir, parents=True, exist_ok=False)
    pipeline = build_pipeline(final_k=20)
    assert isinstance(pipeline.reranker, TechQAReranker)
    index = open_index()
    by_id = {q["QUESTION_ID"]: q for split in ["dev", "fixture"] for q in questions(split)}
    baseline = json.loads((ROOT / "enterprise-ai-agent/evaluation/results/"
                           "techqa_remediation_v4/runs.json").read_text(encoding="utf-8"))
    rewrites = {r["question_id"]: r["trace"]["rewritten_query"] for r in baseline}
    sources = sorted((ROOT / "src/rag").rglob("*.py"))
    manifest: dict[str, Any] = {
        "created_at": datetime.now(UTC).isoformat(),
        "protocol": "open full-corpus stages; IDs only for post-retrieval scoring; "
                    "frozen original parent for passage experiments; no generation",
        "source_hash": hashlib.sha256(b"".join(p.read_bytes() for p in sources)).hexdigest(),
        "questions": CASES + CONTROLS, "controls": CONTROLS,
        "dataset_hash": hashlib.sha256(json.dumps(
            [by_id[k] for k in CASES + CONTROLS], sort_keys=True).encode()).hexdigest(),
    }
    async with httpx.AsyncClient(timeout=60) as client:
        manifest["semantic_index"] = (await client.get(
            "http://127.0.0.1:11435/healthz")).json()
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    for identifier in CASES + CONTROLS:
        LOGGER.info("Diagnosing %s", identifier)
        row = by_id[identifier]
        original = question_text(row)
        rewritten = rewrites.get(identifier, original)
        record: dict[str, Any] = {"id": identifier, "target_document": row["DOCUMENT"],
            "original_query": original, "rewrite_query": rewritten,
            "rewrite_provenance": "archived native enterprise trace" if identifier in rewrites
                                  else "RuleRewriter/original query", "queries": {}}
        for label, query in dict(original=original, rewritten=rewritten).items():
            if label == "rewritten" and query == original:
                record["queries"][label] = {"same_as": "original"}
                continue
            trace: dict[str, list[SearchResult]] = {}
            outcome = await pipeline.retrieve(query, trace=trace)
            plain = await pipeline.retrieve(query)
            if plain.results != outcome.results or plain.diagnostics != outcome.diagnostics:
                raise RuntimeError("Opt-in instrumentation changed pipeline output")
            parts: dict[str, dict[str, float]] = {}
            ranked = await pipeline.reranker.rerank(query, trace["fusion"], limit=30,
                                                  components=parts)
            if ranked[:20] != trace["rerank"]:
                raise RuntimeError("Reranker instrumentation changed scores/ranks")
            dense, sparse = await asyncio.gather(
                pipeline.dense.retrieve(query, limit=100),
                pipeline.sparse.retrieve(query, limit=100),
            )
            if dense[:30] != trace["dense"] or sparse[:30] != trace["sparse"]:
                raise RuntimeError("Candidate limits changed prefix ordering")
            query_record: dict[str, Any] = {"default_output_identical": True,
                "stages": {name: {"target": target(rows, row["DOCUMENT"]),
                                  "results": [serialize(r) for r in rows]}
                           for name, rows in trace.items()}, "reranker_components": parts,
                "dense100_target": target(dense, row["DOCUMENT"]),
                "bm25_100_target": target(sparse, row["DOCUMENT"]), "ablations": []}
            # Frozen branch lists, freshly fused for each candidate limit. Only
            # the offline experimental sorter changes weights; defaults stay intact.
            for candidate_k in [30, 60, 100]:
                fused = reciprocal_rank_fusion([dense[:candidate_k], sparse[:candidate_k]],
                                               limit=candidate_k)
                component_scores: dict[str, dict[str, float]] = {}
                all_ranked = await pipeline.reranker.rerank(
                    query, fused, limit=candidate_k, components=component_scores)
                for profile, weights in WEIGHTS.items():
                    experimental = [replace(r, score=sum(w * component_scores[r.chunk_id][key]
                        for w, key in zip(weights,
                            ["semantic_score", "lexical_score", "bm25_prior"],
                            strict=True))) for r in all_ranked]
                    # Preserve pre-rerank stable tie order, including exact score ties.
                    order = {r.chunk_id: i for i, r in enumerate(fused)}
                    experimental.sort(key=lambda r: (-r.score, order[r.chunk_id]))
                    for rerank_k in [20, 40]:
                        if rerank_k > candidate_k:
                            continue
                        final = experimental[:rerank_k]
                        query_record["ablations"].append({"weights": profile,
                            "candidate_k": candidate_k, "rerank_k": rerank_k,
                            "dense_target": target(dense[:candidate_k], row["DOCUMENT"]),
                            "sparse_target": target(sparse[:candidate_k], row["DOCUMENT"]),
                            "fusion_target": target(fused, row["DOCUMENT"]),
                            "rerank_target": target(final, row["DOCUMENT"]),
                            "final5_target": target(final[:5], row["DOCUMENT"]),
                            "target_components": {r.chunk_id: component_scores[r.chunk_id]
                                for r in fused if r.metadata.get("techqa_document_id")
                                == row["DOCUMENT"]}})
            record["queries"][label] = query_record
        parent = index.get(row["DOCUMENT"])
        if parent:
            text = parent["title"] + "\n\n" + parent["text"]
            # The correct parent is a frozen component fixture, not a retrieval input.
            stages = record["queries"]["original"]["stages"]
            actual = stages["final"]["target"]["chunk"]
            hint = actual["text"] if actual else ""
            record["frozen_parent"] = {"text": text,
                "sha256": hashlib.sha256(text.encode()).hexdigest(), "experiments": []}
            for hint_on in [False, True]:
                for limit in [1, 2, 4]:
                    passages = answer_passages(original, text, limit=limit,
                                               retrieved_excerpt=hint if hint_on else "")
                    record["frozen_parent"]["experiments"].append({"hint_on": hint_on,
                        "hint_available": bool(hint), "limit": limit,
                        "passages": [{"text": p.text, "score": p.relevance,
                                      "start": text.find(p.text),
                                      "end": text.find(p.text)+len(p.text)}
                                     for p in passages]})
        (output / (identifier + ".json")).write_text(json.dumps(record, ensure_ascii=False,
                                                               indent=2), encoding="utf-8")
    manifest["complete"] = True
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    asyncio.run(experiment(args.output))


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    main()
