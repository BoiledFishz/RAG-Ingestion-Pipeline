"""Round 6: graded Verifier with full evidence passages; minimum score chosen on the TUNE split.

    python -m evaluation.chap12_round6 select   # after the score-only run
    python -m evaluation.chap12_round6 decide   # after the run at the selected minimum

Runs (tune split, real model qwen2.5:7b, Multi-Agent, explain + explain_and_data, 150 tasks,
1 repeat, nomic, top_k 8, Critic on), compared with tune_real_r4_base (7b without Verifier):
    results/chap12/tune_real_r6_scores   CHAP12_VERIFIER=graded, no minimum: scores recorded,
                                         nothing withheld
    results/chap12/tune_real_r6_verify   CHAP12_VERIFIER=graded, minimum = selected value
"Correct answerable lost" = answerable tasks correct in the base run and not correct in the
variant (the round 5 acceptance-rate guard also counted refusals of answers that cited the
wrong document, which were already wrong).
Rules, fixed and committed before the runs:
  select  for each minimum m in 2..5, simulate on the score-only run: an answer with score < m
          is withheld (answerable -> not correct; unanswerable -> refusal correct; for
          explain_and_data the data part is kept as recorded). Feasible: correct answerable
          lost <= 3 and net paired wins >= 5 against tune_real_r4_base. Choose the feasible m
          with the largest net (ties: the lower m). No feasible m -> stop; nothing adopted and
          no thresholded run.
  decide  adopt the selected minimum only if the actual thresholded run, against
          tune_real_r4_base, has correct answerable lost <= 3, net paired wins >= 5, a failure
          rate that is not higher, and mean token F1 on answerable tasks answered by both runs
          not lower by more than 0.05.
Writes evaluation/chap12/tune/verifier_selection.json (select) and updates `adopted` and adds
`round6` in tune/real_config.json (decide).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from evaluation.chap12_paired import RESULTS, compare, load

HERE = Path(__file__).resolve().parent / "chap12/tune"
BASE = "tune_real_r4_base"
SCORES = "tune_real_r6_scores"
VERIFY = "tune_real_r6_verify"


def score_of(row: dict[str, Any]) -> int | None:
    detail = str(row.get("verifier") or "")
    if not detail.startswith("score="):
        return None
    return int(detail.removeprefix("score=").split(";")[0])


def simulated_correct(row: dict[str, Any], minimum: int) -> bool:
    s = row["score"]
    score = score_of(row)
    published = row["published"] in (True, "True")
    if not published or score is None or score >= minimum:
        return bool(s.get("correct"))
    if s.get("answerable"):
        return False
    if row["type"] == "explain_and_data":
        return bool(s.get("data_correct")) and bool(s.get("product_matches_gold_doc", True))
    return True


def lost_answerable(base: dict[Any, Any], correct: dict[Any, bool]) -> int:
    return sum(1 for k, r in base.items() if r["score"].get("answerable")
               and r["score"].get("correct") and not correct[k])


def select() -> dict[str, Any]:
    base, scored = load(BASE), load(SCORES)
    if set(base) != set(scored):
        raise ValueError("score-only run does not cover the base tasks")
    unchanged = sum(bool(base[k]["score"].get("correct")) == bool(scored[k]["score"].get(
        "correct")) for k in base)
    histogram: dict[str, int] = {}
    for r in scored.values():
        key = str(score_of(r)) if r["published"] in (True, "True") else "not published"
        histogram[key] = histogram.get(key, 0) + 1
    by_answerable = {lab: {str(m): sum(1 for r in scored.values()
                                       if r["score"].get("answerable") is flag
                                       and score_of(r) == m) for m in range(1, 6)}
                     for lab, flag in (("Y", True), ("N", False))}
    options = []
    for minimum in range(2, 6):
        correct = {k: simulated_correct(r, minimum) for k, r in scored.items()}
        wins = sum(1 for k in base if correct[k] and not base[k]["score"].get("correct"))
        losses = sum(1 for k in base if base[k]["score"].get("correct") and not correct[k])
        withheld = {lab: sum(1 for r in scored.values() if r["score"].get("answerable") is flag
                             and r["published"] in (True, "True")
                             and (score_of(r) or 6) < minimum)
                    for lab, flag in (("Y", True), ("N", False))}
        lost = lost_answerable(base, correct)
        options.append({"min_score": minimum, "wins": wins, "losses": losses,
                        "net": wins - losses, "correct_answerable_lost": lost,
                        "withheld": withheld, "feasible": lost <= 3 and wins - losses >= 5})
    feasible = [o for o in options if o["feasible"]]
    chosen = max(feasible, key=lambda o: (o["net"], -o["min_score"]))["min_score"] \
        if feasible else None
    out = {"split": "tune", "base": BASE, "scores": SCORES,
           "score_only_matches_base_correctness": f"{unchanged}/{len(base)}",
           "score_histogram_published": histogram, "scores_by_answerable": by_answerable,
           "options": options, "selected_min_score": chosen,
           "rule": __doc__.split("select  ")[1].split("decide  ")[0].strip()}
    (HERE / "verifier_selection.json").write_text(json.dumps(out, indent=1) + "\n",
                                                  encoding="utf-8")
    print(json.dumps({k: v for k, v in out.items() if k != "rule"}, indent=1))
    return out


def decide() -> dict[str, Any]:
    selection = json.loads((HERE / "verifier_selection.json").read_text("utf-8-sig"))
    minimum = selection["selected_min_score"]
    config_path = HERE / "real_config.json"
    config = json.loads(config_path.read_text("utf-8-sig"))
    result: dict[str, Any] = {"selected_min_score": minimum, "adopted": False}
    if minimum is not None:
        pair = compare(BASE, VERIFY)
        base, variant = load(BASE), load(VERIFY)
        lost = lost_answerable(base, {k: bool(r["score"].get("correct"))
                                      for k, r in variant.items()})

        def failure(name: str) -> float:
            summary = json.loads((RESULTS / name / "summary.json").read_text("utf-8-sig"))
            return float(summary["systems"]["multi"]["all"]
                         ["failure_rate (failed+timeout)"]["mean"])

        f1 = pair["y_token_f1_both_answered"]
        ok = (lost <= 3 and pair["net"] >= 5 and failure(VERIFY) <= failure(BASE)
              and f1["variant"] >= f1["base"] - 0.05)
        result |= {"correct_answerable_lost": lost, "paired": {
            x: pair[x] for x in ("base_correct", "variant_correct", "wins", "losses", "net",
                                 "mcnemar_p_one_sided", "mcnemar_p_two_sided", "y_token_f1",
                                 "y_token_f1_both_answered")},
            "failure_rate": {"base": failure(BASE), "variant": failure(VERIFY)},
            "adopted": ok}
    config["adopted"]["verifier_min_score"] = minimum if result["adopted"] else None
    config["round6"] = result | {"rule": __doc__.split("decide  ")[1].split("Writes")[0].strip()}
    config_path.write_text(json.dumps(config, ensure_ascii=False, indent=1) + "\n",
                           encoding="utf-8")
    print(json.dumps(result, indent=1))
    return result


if __name__ == "__main__":
    {"select": select, "decide": decide}[sys.argv[1]]()
