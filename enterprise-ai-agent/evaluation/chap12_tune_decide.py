"""Choose the online-profile settings from real-model runs on the TUNE split only.

    python -m evaluation.chap12_tune_decide

Inputs (multi system, tune mixed tasks, explain + explain_and_data, 1 repeat, real model):
    results/chap12/tune_real_base      top_k 8,  max_context_tokens 2400, Critic off
    results/chap12/tune_real_k12       top_k 12, max_context_tokens 3600, Critic off
    results/chap12/tune_real_k16       top_k 16, max_context_tokens 4800, Critic off
    results/chap12/tune_real_critic    top_k 8,  max_context_tokens 2400, Critic on
Rules, fixed and committed before any of these runs:
  depth   take the deeper variant with the higher correct completion over both task types
          (ties: the shallower one); adopt it only if it beats base by >= 0.03, its failure
          rate (failed + timeout) is not higher, and its mean latency is <= 1.5 x base.
  critic  adopt only if explain_and_data correct completion >= base + 0.02 and the
          explain_and_data product match rate is not lower than base.
The two choices are made independently (they act on different parts) and combined.
Output: evaluation/chap12/tune/real_config.json (read by agents.chap12.factory).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
RESULTS = HERE / "results/chap12"
VARIANTS = {
    "base": {"top_k": 8, "max_context_tokens": 2400, "critic": False},
    "k12": {"top_k": 12, "max_context_tokens": 3600, "critic": False},
    "k16": {"top_k": 16, "max_context_tokens": 4800, "critic": False},
    "critic": {"top_k": 8, "max_context_tokens": 2400, "critic": True},
}


def block(name: str, kind: str) -> dict[str, Any]:
    data = json.loads((RESULTS / f"tune_real_{name}/summary.json").read_text("utf-8-sig"))
    if data.get("split") != "tune":
        raise ValueError(f"{name} is not a tune-split run")
    result: dict[str, Any] = data["systems"]["multi"][kind]
    return result


def mean(b: dict[str, Any], key: str) -> float:
    value = b.get(key)
    return float(value["mean"]) if isinstance(value, dict) and value.get("mean") is not None \
        else 0.0


def main() -> None:
    summary: dict[str, Any] = {}
    for name in VARIANTS:
        both = block(name, "all")
        ed = block(name, "explain_and_data")
        summary[name] = {
            "correct_all": mean(both, "correct_completion"),
            "failure_rate": mean(both, "failure_rate (failed+timeout)"),
            "latency_mean_ms": both["latency_ms"]["mean"],
            "correct_ed": mean(ed, "correct_completion"),
            "product_match_ed": mean(ed, "product_matches_gold_doc"),
            "tasks": both["tasks"], "config": VARIANTS[name]}
    base = summary["base"]
    deep = max(("k12", "k16"), key=lambda n: (summary[n]["correct_all"],
                                              -VARIANTS[n]["top_k"]))
    d = summary[deep]
    depth_ok = (d["correct_all"] >= base["correct_all"] + 0.03
                and d["failure_rate"] <= base["failure_rate"]
                and d["latency_mean_ms"] <= 1.5 * base["latency_mean_ms"])
    c = summary["critic"]
    critic_ok = (c["correct_ed"] >= base["correct_ed"] + 0.02
                 and c["product_match_ed"] >= base["product_match_ed"])
    chosen = VARIANTS[deep] if depth_ok else VARIANTS["base"]
    adopted = {"top_k": chosen["top_k"], "max_context_tokens": chosen["max_context_tokens"],
               "critic": critic_ok}
    out = {"split": "tune", "rules": __doc__.split("Rules, fixed")[1].split("Output:")[0].strip(),
           "variants": summary, "best_depth_variant": deep, "depth_adopted": depth_ok,
           "critic_adopted": critic_ok, "adopted": adopted}
    (HERE / "chap12/tune/real_config.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in out.items() if k != "rules"}, indent=1))


if __name__ == "__main__":
    main()
