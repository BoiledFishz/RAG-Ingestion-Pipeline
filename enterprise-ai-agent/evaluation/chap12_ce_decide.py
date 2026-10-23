"""Round 3 decision: adopt a cross-encoder reranker for the online profile or not.

    python -m evaluation.chap12_ce_decide

Compares, on the TUNE split with the real model (Multi-Agent, explain + explain_and_data,
150 tasks, 1 repeat), each screened cross-encoder run `results/chap12/tune_real_<choice>`
against the currently adopted configuration `results/chap12/tune_real_critic`
(nomic rerank, top_k 8, Critic on). Rule, fixed and committed before the runs:
  adopt the cross-encoder with the higher correct completion, only if it is at least 0.03
  above the current configuration, its failure rate is not higher and its mean latency is
  at most 1.5 x the current one. Otherwise keep nomic.
Updates `adopted.reranker` in evaluation/chap12/tune/real_config.json.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
RESULTS = HERE / "results/chap12"
CONFIG = HERE / "chap12/tune/real_config.json"
STUDY = HERE / "chap12/tune/ce_study.json"


def stats(name: str) -> dict[str, Any] | None:
    path = RESULTS / f"tune_real_{name}/summary.json"
    if not path.is_file():
        return None
    data = json.loads(path.read_text("utf-8-sig"))
    if data.get("split") != "tune":
        raise ValueError(f"{name} is not a tune-split run")
    b = data["systems"]["multi"]["all"]
    return {"correct_all": float(b["correct_completion"]["mean"]),
            "failure_rate": float(b["failure_rate (failed+timeout)"]["mean"]),
            "latency_mean_ms": float(b["latency_ms"]["mean"])}


def main() -> None:
    current = stats("critic")
    if current is None:
        raise FileNotFoundError("tune_real_critic (current configuration) is missing")
    screened = json.loads(STUDY.read_text("utf-8"))["variants"]
    candidates = {}
    for choice, entry in screened.items():
        if not entry["proceed"]:
            continue
        result = stats(choice)
        if result is None:
            raise FileNotFoundError(f"tune_real_{choice} missing for a screened variant")
        candidates[choice] = result
    passing = {c: r for c, r in candidates.items()
               if r["correct_all"] >= current["correct_all"] + 0.03
               and r["failure_rate"] <= current["failure_rate"]
               and r["latency_mean_ms"] <= 1.5 * current["latency_mean_ms"]}
    adopted = max(passing, key=lambda c: passing[c]["correct_all"]) if passing else "nomic"
    config = json.loads(CONFIG.read_text("utf-8"))
    config["adopted"]["reranker"] = adopted
    config["round3"] = {"current": current, "candidates": candidates,
                        "screened_out": [c for c, e in screened.items() if not e["proceed"]],
                        "rule": __doc__.split("Rule, fixed")[1].split("Updates")[0].strip(),
                        "adopted_reranker": adopted}
    CONFIG.write_text(json.dumps(config, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(json.dumps(config["round3"], indent=1))


if __name__ == "__main__":
    main()
