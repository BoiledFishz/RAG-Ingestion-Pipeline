"""Round 4 decision: cross-encoder ORDER with nomic ACCEPTANCE, or keep nomic.

    python -m evaluation.chap12_order_decide

Variants (tools/sample_retriever.py, agents/chap12/cross_encoder.OrderOnlyReranker): the
cross-encoder orders the fused candidates (so it decides which documents fill top_k); every
document keeps its nomic reranker score and is accepted with the existing nomic threshold
(tune/thresholds.json `nomic_rerank`, 0.6568). No new threshold is calibrated.

All runs: TUNE split, real model, Multi-Agent, explain + explain_and_data, 150 tasks,
1 repeat, top_k 8, Critic on, same Ollama version (the round 3 Ollama 0.40.5 -> 0.40.6
confound is removed by re-running the current configuration first):
    results/chap12/tune_real_r4_base             nomic order + nomic acceptance (current)
    results/chap12/tune_real_r4_ce_minilm_order  ms-marco-MiniLM-L-6-v2 order
    results/chap12/tune_real_r4_ce_bge_order     bge-reranker-base order
Rule, fixed and committed before the runs:
  adopt the order variant with the higher correct completion, only if it is at least 0.03
  above tune_real_r4_base, its failure rate is not higher and its mean latency is at most
  1.5 x tune_real_r4_base. Otherwise keep nomic.
Updates `adopted.reranker` and adds `round4` in evaluation/chap12/tune/real_config.json.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
RESULTS = HERE / "results/chap12"
CONFIG = HERE / "chap12/tune/real_config.json"
VARIANTS = ("ce_minilm_order", "ce_bge_order")


def stats(name: str) -> dict[str, Any]:
    path = RESULTS / f"tune_real_r4_{name}/summary.json"
    data = json.loads(path.read_text("utf-8-sig"))
    if data.get("split") != "tune":
        raise ValueError(f"{name} is not a tune-split run")
    multi = data["systems"]["multi"]
    b, ed = multi["all"], multi["explain_and_data"]

    def mean(block: dict[str, Any], key: str) -> float | None:
        value = block.get(key)
        return float(value["mean"]) if isinstance(value, dict) and value.get("mean") is not None \
            else None

    return {"correct_all": float(b["correct_completion"]["mean"]),
            "failure_rate": float(b["failure_rate (failed+timeout)"]["mean"]),
            "latency_mean_ms": float(b["latency_ms"]["mean"]),
            "correct_explain": mean(multi["explain"], "correct_completion"),
            "correct_ed": mean(ed, "correct_completion"),
            "y_accept": mean(b, "y_accept"), "n_refuse": mean(b, "n_refuse"),
            "y_gold_cited": mean(b, "y_gold_cited"), "retrieval_y": b.get("retrieval_y"),
            "tasks": b["tasks"]}


def main() -> None:
    base = stats("base")
    candidates = {v: stats(v) for v in VARIANTS}
    passing = {v: r for v, r in candidates.items()
               if r["correct_all"] >= base["correct_all"] + 0.03
               and r["failure_rate"] <= base["failure_rate"]
               and r["latency_mean_ms"] <= 1.5 * base["latency_mean_ms"]}
    adopted = max(passing, key=lambda v: passing[v]["correct_all"]) if passing else "nomic"
    config = json.loads(CONFIG.read_text("utf-8-sig"))
    config["adopted"]["reranker"] = adopted
    config["round4"] = {"base": base, "candidates": candidates,
                        "rule": __doc__.split("Rule, fixed")[1].split("Updates")[0].strip(),
                        "adopted_reranker": adopted}
    CONFIG.write_text(json.dumps(config, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in config["round4"].items() if k != "rule"}, indent=1))


if __name__ == "__main__":
    main()
