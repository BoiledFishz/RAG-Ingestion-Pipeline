"""Round 5 decision: answerability Verifier and a larger generation model.

    python -m evaluation.chap12_round5_decide

All runs: TUNE split, real model, Multi-Agent, explain + explain_and_data, 150 tasks,
1 repeat, nomic rerank, top_k 8, Critic on. Comparisons are paired (evaluation/chap12_paired).
    7b base           results/chap12/tune_real_r5_base_7b if present (re-run because the Ollama
                      version changed), else tune_real_r4_base (qwen2.5:7b, Ollama 0.40.6;
                      reproduced round 2 exactly, 150/150)
    7b + Verifier     results/chap12/tune_real_r5_verify_7b
    14b               results/chap12/tune_real_r5_base_14b      (qwen2.5:14b; skipped if the
    14b + Verifier    results/chap12/tune_real_r5_verify_14b     model is not available)
Rules, fixed and committed before the runs:
  model     adopt qwen2.5:14b only if, against 7b base, net paired wins >= 5 with one-sided
            exact McNemar p < 0.10, its failure rate is not higher, mean answerable token F1
            is not lower by more than 0.05, and mean latency <= 2.5 x 7b base.
  verifier  on the adopted model, against the same model without the Verifier: adopt only if
            the unanswerable refusal rate rises by >= 0.25, the answerable acceptance rate
            falls by <= 0.05, paired wins >= paired losses, the failure rate is not higher
            and mean answerable token F1 is not lower by more than 0.05.
Updates `adopted.model` and `adopted.verifier` and adds `round5` in tune/real_config.json.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from evaluation.chap12_paired import RESULTS, compare

CONFIG = Path(__file__).resolve().parent / "chap12/tune/real_config.json"


def stats(name: str) -> dict[str, Any]:
    data = json.loads((RESULTS / name / "summary.json").read_text("utf-8-sig"))
    if data.get("split") != "tune":
        raise ValueError(f"{name} is not a tune-split run")
    b = data["systems"]["multi"]["all"]

    def mean(key: str) -> float:
        return float(b[key]["mean"])

    return {"correct_all": mean("correct_completion"),
            "failure_rate": mean("failure_rate (failed+timeout)"),
            "latency_mean_ms": float(b["latency_ms"]["mean"]),
            "y_accept": mean("y_accept"), "n_refuse": mean("n_refuse"),
            "y_gold_cited": mean("y_gold_cited"), "llm_calls_mean": b.get("llm_calls_mean"),
            "tasks": b["tasks"]}


def exists(name: str) -> bool:
    return (RESULTS / name / "summary.json").is_file()


def main() -> None:
    base7 = "tune_real_r5_base_7b" if exists("tune_real_r5_base_7b") else "tune_real_r4_base"
    out: dict[str, Any] = {"base_7b": base7, "runs": {}, "paired": {}}
    names = {"7b": base7, "7b_verify": "tune_real_r5_verify_7b",
             "14b": "tune_real_r5_base_14b", "14b_verify": "tune_real_r5_verify_14b"}
    for key, name in names.items():
        out["runs"][key] = stats(name) if exists(name) else None

    def paired(a: str, b: str) -> dict[str, Any] | None:
        if not (exists(names[a]) and exists(names[b])):
            return None
        result = compare(names[a], names[b])
        out["paired"][f"{b} vs {a}"] = result
        return result

    runs = out["runs"]
    model, model_ok = "qwen2.5:7b", False
    p14 = paired("7b", "14b")
    if p14 is not None:
        r7, r14 = runs["7b"], runs["14b"]
        model_ok = (p14["net"] >= 5 and p14["mcnemar_p_one_sided"] < 0.10
                    and r14["failure_rate"] <= r7["failure_rate"]
                    and p14["y_token_f1"]["variant"] >= p14["y_token_f1"]["base"] - 0.05
                    and r14["latency_mean_ms"] <= 2.5 * r7["latency_mean_ms"])
        model = "qwen2.5:14b" if model_ok else model
    size = "14b" if model_ok else "7b"
    for s in ("7b", "14b"):
        paired(s, f"{s}_verify")
    pv = out["paired"].get(f"{size}_verify vs {size}")
    verify_ok = False
    if pv is not None:
        b, v = runs[size], runs[f"{size}_verify"]
        verify_ok = (v["n_refuse"] >= b["n_refuse"] + 0.25
                     and v["y_accept"] >= b["y_accept"] - 0.05
                     and pv["wins"] >= pv["losses"]
                     and v["failure_rate"] <= b["failure_rate"]
                     and pv["y_token_f1"]["variant"] >= pv["y_token_f1"]["base"] - 0.05)
    config = json.loads(CONFIG.read_text("utf-8-sig"))
    config["adopted"]["model"] = model
    config["adopted"]["verifier"] = verify_ok
    out |= {"rules": __doc__.split("Rules, fixed")[1].split("Updates")[0].strip(),
            "model_14b_run": p14 is not None, "model_adopted": model,
            "verifier_evaluated_on": size if pv is not None else None,
            "verifier_adopted": verify_ok}
    config["round5"] = out
    CONFIG.write_text(json.dumps(config, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    brief = {k: v for k, v in out.items() if k not in {"rules", "paired"}}
    brief["paired"] = {k: {x: v[x] for x in ("wins", "losses", "net", "mcnemar_p_one_sided",
                                              "y_token_f1")}
                       for k, v in out["paired"].items()}
    print(json.dumps(brief, indent=1))


if __name__ == "__main__":
    main()
