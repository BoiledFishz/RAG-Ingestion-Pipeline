"""Round 3: cross-encoder rerankers on the TUNE split only (no LLM; local models).

    python -m evaluation.chap12_ce_study

For each cross-encoder (`ce_minilm` = cross-encoder/ms-marco-MiniLM-L-6-v2,
`ce_bge` = BAAI/bge-reranker-base) over the same hybrid candidates as the RAG Worker:
  1. document-level recall of the gold answer document on the 112 answerable tune questions;
  2. the acceptance threshold, calibrated exactly like the nomic and MiniLM thresholds
     (highest top-1 score that keeps the Project 1 answer acceptance), written to
     tune/thresholds.json as `<choice>_rerank`.
Screening rule, fixed before the run: a cross-encoder goes on to the real-model tune
comparison only if its R@8 is at least 0.03 above the nomic reranker's tune R@8
(tune/retrieval_report_tune_nomic.json). Output: tune/ce_study.json.
"""

from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path
from typing import Any

from rag.techqa.data import ROOT

from evaluation.chap12_retrieval_tune import calibrate, evaluate, merged_thresholds

HERE = Path(__file__).resolve().parent / "chap12" / "tune"
CHOICES = ("ce_minilm", "ce_bge")
ENV = {"ce_minilm": "CHAP12_CE_MINILM_THRESHOLD", "ce_bge": "CHAP12_CE_BGE_THRESHOLD"}
DEPTH = 20


async def main_async() -> None:
    from agents.chap12.cross_encoder import manifest
    from tools.sample_retriever import SampleRetrieverTool

    os.environ["CHAP12_GAP_GATE"] = ""
    index = ROOT / ".rag_data/chap12_tune.sqlite"
    tasks = [json.loads(x) for x in (HERE / "tasks.jsonl").read_text("utf-8").splitlines()]
    rows = [json.loads(x) for x in (HERE / "gold.jsonl").read_text("utf-8").splitlines()]
    gold = {g["task_id"]: g["document"] for g in rows if g["answerable"] == "Y"}
    answerable = {g["task_id"]: g["answerable"] == "Y" for g in rows}
    y_tasks = [t for t in tasks if t["task_id"] in gold]
    nomic = json.loads((HERE / "retrieval_report_tune_nomic.json").read_text("utf-8"))
    nomic_r8 = float(nomic["hybrid+nomic_rerank"]["R@8"]["value"])
    report: dict[str, Any] = {"split": "tune", "nomic_R@8": nomic_r8,
                              "rule": "proceed iff R@8 >= nomic R@8 + 0.03", "variants": {}}
    thresholds = merged_thresholds(HERE)
    for choice in CHOICES:
        os.environ[ENV[choice]] = "0"  # recall ignores acceptance thresholds
        tool = SampleRetrieverTool(index, rerank=choice)
        recall = await evaluate(tool, y_tasks, gold, DEPTH)
        calibration = await calibrate(tool, tasks, answerable)
        os.environ.pop(ENV[choice])
        thresholds[f"{choice}_rerank"] = calibration
        report["variants"][choice] = {
            "model": manifest(choice), "recall": recall, "calibration": calibration,
            "proceed": recall["R@8"]["value"] >= nomic_r8 + 0.03}
        print(choice, recall["R@8"]["value"], recall["MRR"], calibration.get("threshold"),
              flush=True)
    (HERE / "thresholds.json").write_text(json.dumps(thresholds, indent=2) + "\n",
                                          encoding="utf-8")
    (HERE / "ce_study.json").write_text(json.dumps(report, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({k: v["proceed"] for k, v in report["variants"].items()}))


def main() -> None:
    asyncio.run(main_async())


if __name__ == "__main__":
    main()
