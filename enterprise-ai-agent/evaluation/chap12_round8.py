"""Round 8: select with the Project 1 prompt, then a separate judge call (two LLM calls).

    python -m evaluation.chap12_round8

Run (real model qwen2.5:7b, Multi-Agent, explain + explain_and_data, 150 tasks, 1 repeat,
nomic, top_k 8, Critic on, no Verifier, layer trace on):
    results/chap12/tune_real_r8_judged   CHAP12_SELECTOR=judged
compared with the Project 1 selector on the same Ollama version: results/chap12/tune_real_r8_base
if the runner had to re-run it (Ollama no longer 0.40.7), else tune_real_r7_base (0.40.7).
Rules, fixed and committed before the run:
  adopt  adopt the judged selector only if, against the base: correct answerable answers
         lost <= 3, net paired wins >= 5, failure rate not higher, and mean token F1 on
         answerable tasks answered by both runs not lower by more than 0.05.
  gate   (diagnosis only) on the judged run's trace, simulate a hard gate before the LLM:
         refuse when the top returned rerank score < T, T in 0.60..0.80 step 0.02, with the
         same two counts. A feasible T is a candidate for a separate pre-registered run.
Updates `adopted.selector` and adds `round8` in tune/real_config.json.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from evaluation.chap12_paired import RESULTS, compare, load
from evaluation.chap12_round6 import lost_answerable

HERE = Path(__file__).resolve().parent / "chap12/tune"
BASE = "tune_real_r8_base" if (RESULTS / "tune_real_r8_base/summary.json").is_file() \
    else "tune_real_r7_base"
STRICT = "tune_real_r8_judged"


def summary(name: str) -> dict[str, Any]:
    data = json.loads((RESULTS / name / "summary.json").read_text("utf-8-sig"))
    b = data["systems"]["multi"]["all"]
    return {k: float(b[v]["mean"]) for k, v in (
        ("correct_all", "correct_completion"), ("failure_rate", "failure_rate (failed+timeout)"),
        ("y_accept", "y_accept"), ("n_refuse", "n_refuse"), ("y_gold_cited", "y_gold_cited"))} \
        | {"latency_mean_ms": float(b["latency_ms"]["mean"])}


def gate_simulation(base: dict[Any, Any]) -> list[dict[str, Any]]:
    rows = {(r["task_id"], int(r.get("repeat", 1))): r for r in map(
        json.loads, (RESULTS / STRICT / "traces.jsonl").read_text("utf-8-sig").splitlines())
        if r["system"] == "multi"}
    out = []
    for step in range(11):
        t = round(0.60 + 0.02 * step, 2)
        correct: dict[Any, bool] = {}
        for k, r in rows.items():
            s = r["score"]
            returned = (r["layers"].get("retrieval") or {}).get("returned", [])
            top = returned[0]["score"] if returned else 0.0
            if top >= t or not r.get("published"):
                correct[k] = bool(s.get("correct"))
            elif s.get("answerable"):
                correct[k] = False
            elif r["type"] == "explain_and_data":
                correct[k] = bool(s.get("data_correct")) and bool(
                    s.get("product_matches_gold_doc", True))
            else:
                correct[k] = True
        wins = sum(1 for k in base if correct[k] and not base[k]["score"].get("correct"))
        losses = sum(1 for k in base if base[k]["score"].get("correct") and not correct[k])
        lost = lost_answerable(base, correct)
        out.append({"threshold": t, "wins": wins, "losses": losses, "net": wins - losses,
                    "correct_answerable_lost": lost,
                    "feasible": lost <= 3 and wins - losses >= 5})
    return out


def main() -> None:
    base = load(BASE)
    pair = compare(BASE, STRICT)
    lost = lost_answerable(base, {k: bool(r["score"].get("correct"))
                                  for k, r in load(STRICT).items()})
    b, v = summary(BASE), summary(STRICT)
    f1 = pair["y_token_f1_both_answered"]
    ok = (lost <= 3 and pair["net"] >= 5 and v["failure_rate"] <= b["failure_rate"]
          and f1["variant"] >= f1["base"] - 0.05)
    reproduction = compare("tune_real_r7_base", BASE) if BASE != "tune_real_r7_base" else None
    result = {"base_run": BASE, "base_reproduces_r7": None if reproduction is None else {
                  x: reproduction[x] for x in ("base_correct", "variant_correct", "wins",
                                                "losses")},
              "base": b, "judged": v, "correct_answerable_lost": lost,
              "paired": {x: pair[x] for x in ("base_correct", "variant_correct", "wins",
                                              "losses", "net", "mcnemar_p_one_sided",
                                              "y_token_f1", "y_token_f1_both_answered")},
              "adopted": ok, "gate_simulation": gate_simulation(base)}
    config_path = HERE / "real_config.json"
    config = json.loads(config_path.read_text("utf-8-sig"))
    config["adopted"]["selector"] = "judged" if ok else "project1"
    config["round8"] = result | {"rule": __doc__.split("Rules, fixed")[1].split("Updates")[0]
                                 .strip()}
    config_path.write_text(json.dumps(config, ensure_ascii=False, indent=1) + "\n",
                           encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
