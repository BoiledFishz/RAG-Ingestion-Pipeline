"""Round 10: rerank prior from the fused rank, with candidate_k 30 or 50 (TUNE split).

    python -m evaluation.chap12_round10

Current configuration (adopted in round 9): nomic rerank, top_k 8, Critic on, 7B selector +
14B judge. Variants change only the retriever:
    results/chap12/tune_real_r10_fused30   CHAP12_RERANK_PRIOR=fused, CHAP12_CANDIDATE_K=30
    results/chap12/tune_real_r10_fused50   CHAP12_RERANK_PRIOR=fused, CHAP12_CANDIDATE_K=50
Base: tune_real_r9_judged14 (Ollama 0.40.9), or results/chap12/tune_real_r10_base when the
runner had to re-run the current configuration on a newer Ollama.
Offline motivation (results/chap12/recall_rerank_study.json, diagnosis): gold in the top 8 74 ->
82 of 112 with the fused prior at 30 candidates; 50 candidates could not be scored offline.
Acceptance thresholds are unchanged.
Rules, fixed and committed before the runs:
  adopt  a variant is eligible only if, against the base: correct answerable answers lost <= 3,
         net paired wins >= 5, failure rate not higher, and mean token F1 on answerable tasks
         answered by both runs not lower by more than 0.05. Adopt the eligible variant with the
         larger net (ties: candidate_k 30). Latency is reported, not gated.
Updates `adopted.rerank_prior` / `adopted.candidate_k` and adds `round10` in real_config.json.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from evaluation.chap12_paired import RESULTS, compare, load
from evaluation.chap12_round6 import lost_answerable

HERE = Path(__file__).resolve().parent / "chap12/tune"
BASE = "tune_real_r10_base" if (RESULTS / "tune_real_r10_base/summary.json").is_file() \
    else "tune_real_r9_judged14"
VARIANTS = {"fused30": 30, "fused50": 50}


def summary(name: str) -> dict[str, Any]:
    b = json.loads((RESULTS / name / "summary.json").read_text("utf-8-sig"))["systems"]["multi"][
        "all"]
    out = {k: float(b[v]["mean"]) for k, v in (
        ("correct_all", "correct_completion"), ("failure_rate", "failure_rate (failed+timeout)"),
        ("y_accept", "y_accept"), ("n_refuse", "n_refuse"), ("y_gold_cited", "y_gold_cited"))}
    return out | {"latency_mean_ms": float(b["latency_ms"]["mean"]),
                  "retrieval_y": b.get("retrieval_y")}


def main() -> None:
    base_rows, b = load(BASE), summary(BASE)
    result: dict[str, Any] = {"base_run": BASE, "base": b, "variants": {}}
    if BASE != "tune_real_r9_judged14":
        r = compare("tune_real_r9_judged14", BASE)
        result["base_reproduces_r9"] = {x: r[x] for x in ("base_correct", "variant_correct",
                                                          "wins", "losses")}
    eligible = {}
    for name, k in VARIANTS.items():
        run = f"tune_real_r10_{name}"
        pair = compare(BASE, run)
        lost = lost_answerable(base_rows, {key: bool(r["score"].get("correct"))
                                           for key, r in load(run).items()})
        v = summary(run)
        f1 = pair["y_token_f1_both_answered"]
        ok = (lost <= 3 and pair["net"] >= 5 and v["failure_rate"] <= b["failure_rate"]
              and f1["variant"] >= f1["base"] - 0.05)
        result["variants"][name] = {"candidate_k": k, "summary": v,
                                    "correct_answerable_lost": lost, "eligible": ok,
                                    "paired": {x: pair[x] for x in (
                                        "base_correct", "variant_correct", "wins", "losses",
                                        "net", "mcnemar_p_one_sided",
                                        "y_token_f1_both_answered")}}
        if ok:
            eligible[name] = (pair["net"], -k)
    chosen = max(eligible, key=lambda n: eligible[n]) if eligible else None
    config_path = HERE / "real_config.json"
    config = json.loads(config_path.read_text("utf-8-sig"))
    config["adopted"]["rerank_prior"] = "fused" if chosen else "bm25"
    config["adopted"]["candidate_k"] = VARIANTS[chosen] if chosen else 30
    result["adopted"] = chosen
    config["round10"] = result | {"rule": __doc__.split("Rules, fixed")[1].split("Updates")[0]
                                  .strip()}
    config_path.write_text(json.dumps(config, ensure_ascii=False, indent=1) + "\n",
                           encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
