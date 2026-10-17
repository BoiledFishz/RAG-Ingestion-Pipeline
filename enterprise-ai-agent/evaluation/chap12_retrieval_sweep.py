"""Item 9: small, pre-registered retrieval sweep on the TUNE split only.

    python -m evaluation.chap12_retrieval_sweep            (resumable; offline, MiniLM rerank)

Grid fixed before the run (10 variants):
  rerank weights (semantic, lexical, BM25 prior):
      (0.5, 0.3, 0.2) current | (0.6, 0.2, 0.2) | (0.4, 0.2, 0.4) | (0.3, 0.2, 0.5)
      | (0.5, 0.1, 0.4)
  candidate depth (candidate_k, rerank_k): (30, 20) current | (60, 30)
Adoption rule (fixed before the run): take the variant with the highest R@8 (ties: higher MRR,
then the current setting); adopt it only if R@8 >= current + 0.03 and MRR >= current - 0.01.
Otherwise keep the current setting. An adopted setting gets a new acceptance threshold from the
same tune calibration as before (chap12_retrieval_tune.calibrate).
Output: evaluation/chap12/tune/retrieval_sweep.json (+ thresholds.json when adopted).
"""

from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path
from typing import Any

from rag.techqa.data import ROOT

from evaluation.chap12_retrieval_tune import calibrate, evaluate

HERE = Path(__file__).resolve().parent / "chap12" / "tune"
OUT = HERE / "retrieval_sweep.json"
WEIGHTS = [(0.5, 0.3, 0.2), (0.6, 0.2, 0.2), (0.4, 0.2, 0.4), (0.3, 0.2, 0.5), (0.5, 0.1, 0.4)]
DEPTHS = [(30, 20), (60, 30)]
CURRENT = "w=0.5/0.3/0.2 k=30/20"
DEPTH = 20


def name(weights: tuple[float, float, float], depth: tuple[int, int]) -> str:
    return "w=" + "/".join(str(w) for w in weights) + f" k={depth[0]}/{depth[1]}"


def build(index: Path, weights: tuple[float, float, float], depth: tuple[int, int]) -> Any:
    from dataclasses import replace

    from tools.sample_retriever import SampleRetrieverTool

    tool = SampleRetrieverTool(index, rerank="minilm")
    reranker: Any = tool.pipeline.reranker
    reranker.weights = weights
    tool.pipeline.config = replace(tool.pipeline.config, candidate_k=depth[0], rerank_k=depth[1])
    return tool


def choose(report: dict[str, Any]) -> dict[str, Any]:
    current = report[CURRENT]
    ranked = sorted(report, key=lambda k: (report[k]["R@8"]["value"], report[k]["MRR"],
                                           k == CURRENT), reverse=True)
    best = ranked[0]
    adopt = (best != CURRENT
             and report[best]["R@8"]["value"] >= current["R@8"]["value"] + 0.03
             and report[best]["MRR"] >= current["MRR"] - 0.01)
    return {"best": best, "adopted": best if adopt else CURRENT, "changed": adopt}


async def main_async() -> None:
    os.environ["CHAP12_MINILM_THRESHOLD"] = "0"  # recall ignores acceptance thresholds
    os.environ["CHAP12_GAP_GATE"] = ""
    index = ROOT / ".rag_data/chap12_tune.sqlite"
    tasks = [json.loads(x) for x in (HERE / "tasks.jsonl").read_text("utf-8").splitlines()]
    rows = [json.loads(x) for x in (HERE / "gold.jsonl").read_text("utf-8").splitlines()]
    gold = {g["task_id"]: g["document"] for g in rows if g["answerable"] == "Y"}
    answerable = {g["task_id"]: g["answerable"] == "Y" for g in rows}
    y_tasks = [t for t in tasks if t["task_id"] in gold]
    state: dict[str, Any] = json.loads(OUT.read_text("utf-8")) if OUT.is_file() else {}
    report: dict[str, Any] = state.get("variants", {})
    for depth in DEPTHS:
        for weights in WEIGHTS:
            key = name(weights, depth)
            if key in report:
                continue
            report[key] = await evaluate(build(index, weights, depth), y_tasks, gold, DEPTH)
            OUT.write_text(json.dumps({"split": "tune", "variants": report}, indent=1) + "\n",
                           encoding="utf-8")
            print(key, report[key]["R@8"]["value"], report[key]["MRR"], flush=True)
    decision = choose(report)
    result = {"split": "tune", "variants": report, "decision": decision,
              "rule": "max R@8; adopt only if R@8 >= current + 0.03 and MRR >= current - 0.01"}
    if decision["changed"] and "calibration" not in state:
        weights_text, depth_text = decision["adopted"][2:].split(" k=")
        w = [float(x) for x in weights_text.split("/")]
        d = [int(x) for x in depth_text.split("/")]
        os.environ.pop("CHAP12_MINILM_THRESHOLD")
        tool = build(index, (w[0], w[1], w[2]), (d[0], d[1]))
        os.environ["CHAP12_MINILM_THRESHOLD"] = "0"
        result["calibration"] = await calibrate(tool, tasks, answerable)
    elif "calibration" in state:
        result["calibration"] = state["calibration"]
    OUT.write_text(json.dumps(result, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in result.items() if k != "variants"}, indent=1))


def main() -> None:
    asyncio.run(main_async())


if __name__ == "__main__":
    main()
