"""Round 9: select with qwen2.5:7b (Project 1 prompt), judge with qwen2.5:14b (round 8 prompt).

    python -m evaluation.chap12_round9

Round 8 showed the judge direction works (unanswerable answered 35 -> 8) but the 7B judge vetoed
22 previously correct answers, often calling a same-family IBM document a "different product".
Only the judge model changes here; prompt, rules and everything else are as in round 8.
Run (Multi-Agent, explain + explain_and_data, 150 tasks, 1 repeat, nomic, top_k 8, Critic on,
layer trace on):
    results/chap12/tune_real_r9_judged14   CHAP12_SELECTOR=judged, CHAP12_JUDGE_MODEL=qwen2.5:14b
compared with the Project 1 selector on the same Ollama version: results/chap12/tune_real_r9_base
if the runner had to re-run it (Ollama no longer 0.40.8), else tune_real_r8_base (0.40.8).
Rules, fixed and committed before the run:
  adopt  adopt only if, against the base: correct answerable answers lost <= 3, net paired
         wins >= 5, failure rate not higher, and mean token F1 on answerable tasks answered by
         both runs not lower by more than 0.05. Latency is reported, not gated.
  gate   (diagnosis only) simulate a hard gate on the top rerank score, T in 0.60..0.80.
Also reported (not part of the rule): paired comparison with the 7B judge (tune_real_r8_judged).
Updates `adopted.selector` / `adopted.judge_model` and adds `round9` in tune/real_config.json.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from evaluation.chap12_paired import RESULTS, compare, load
from evaluation.chap12_round6 import lost_answerable

HERE = Path(__file__).resolve().parent / "chap12/tune"
BASE = "tune_real_r9_base" if (RESULTS / "tune_real_r9_base/summary.json").is_file() \
    else "tune_real_r8_base"
STRICT = "tune_real_r9_judged14"


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
    reproduction = compare("tune_real_r8_base", BASE) if BASE != "tune_real_r8_base" else None
    vs7 = compare("tune_real_r8_judged", STRICT)
    result = {"base_run": BASE, "vs_7b_judge": {x: vs7[x] for x in (
                  "base_correct", "variant_correct", "wins", "losses", "net")},
              "base_reproduces_r8": None if reproduction is None else {
                  x: reproduction[x] for x in ("base_correct", "variant_correct", "wins",
                                                "losses")},
              "base": b, "judged14": v, "correct_answerable_lost": lost,
              "paired": {x: pair[x] for x in ("base_correct", "variant_correct", "wins",
                                              "losses", "net", "mcnemar_p_one_sided",
                                              "y_token_f1", "y_token_f1_both_answered")},
              "adopted": ok, "gate_simulation": gate_simulation(base)}
    config_path = HERE / "real_config.json"
    config = json.loads(config_path.read_text("utf-8-sig"))
    config["adopted"]["selector"] = "judged" if ok else "project1"
    config["adopted"]["judge_model"] = "qwen2.5:14b" if ok else None
    config["round9"] = result | {"rule": __doc__.split("Rules, fixed")[1].split("Updates")[0]
                                 .strip()}
    config_path.write_text(json.dumps(config, ensure_ascii=False, indent=1) + "\n",
                           encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
