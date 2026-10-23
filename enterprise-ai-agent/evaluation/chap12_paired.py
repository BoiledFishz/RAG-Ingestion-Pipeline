"""Paired comparison of two runs on the same tasks (round 5, item 4 of the retrospective).

    python -m evaluation.chap12_paired BASE VARIANT [--system multi]
    python -m evaluation.chap12_paired --retro      # rounds 2-4, report only

Means of 150 binary outcomes have a 95% CI of about +/-0.08, wider than the +0.03 adoption
margins used so far. Both runs answer the same tasks, so the informative quantity is the
discordant pairs: wins (base wrong, variant right) and losses (base right, variant wrong).
The exact McNemar test is the binomial test on those pairs with p = 0.5.
Also reported, because "correct" for answerable questions only checks that the gold document
is cited: mean token F1 of the answer against the gold answer over answerable tasks
(refused = 0) and over answerable tasks answered by both runs.
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any

RESULTS = Path(__file__).resolve().parent / "results/chap12"
RETRO = {  # (round, base, variants) exactly as decided at the time; this is report only
    "round2": ("tune_real_base", ["tune_real_k12", "tune_real_k16", "tune_real_critic"]),
    "round3": ("tune_real_critic", ["tune_real_ce_minilm", "tune_real_ce_bge"]),
    "round4": ("tune_real_r4_base", ["tune_real_r4_ce_minilm_order",
                                     "tune_real_r4_ce_bge_order"]),
}


def load(name: str, system: str = "multi") -> dict[tuple[str, int], dict[str, Any]]:
    rows = [json.loads(x) for x in (RESULTS / name / "runs.jsonl").read_text(
        "utf-8-sig").splitlines() if x.strip()]
    return {(r["task_id"], int(r.get("repeat", 1))): r for r in rows if r["system"] == system}


def binom_tail(k: int, n: int) -> float:
    """P(X >= k) for X ~ Binomial(n, 0.5)."""
    return sum(math.comb(n, i) for i in range(k, n + 1)) / 2 ** n if n else 1.0


def compare(base_name: str, variant_name: str, system: str = "multi") -> dict[str, Any]:
    base, variant = load(base_name, system), load(variant_name, system)
    keys = sorted(set(base) & set(variant))
    if len(keys) != len(base) or len(keys) != len(variant):
        raise ValueError(f"{base_name} and {variant_name} do not cover the same tasks")
    wins = [k[0] for k in keys if not base[k]["score"].get("correct")
            and variant[k]["score"].get("correct")]
    losses = [k[0] for k in keys if base[k]["score"].get("correct")
              and not variant[k]["score"].get("correct")]
    n = len(wins) + len(losses)
    y = [k for k in keys if base[k]["score"].get("answerable") is True]
    both = [k for k in y if base[k]["published"] in (True, "True")
            and variant[k]["published"] in (True, "True")]

    def f1(rows: dict[tuple[str, int], dict[str, Any]], ks: list[tuple[str, int]]) -> float:
        return round(sum(float(rows[k]["score"].get("token_f1") or 0) for k in ks)
                     / max(len(ks), 1), 4)

    return {"base": base_name, "variant": variant_name, "tasks": len(keys),
            "base_correct": sum(bool(base[k]["score"].get("correct")) for k in keys),
            "variant_correct": sum(bool(variant[k]["score"].get("correct")) for k in keys),
            "wins": len(wins), "losses": len(losses), "net": len(wins) - len(losses),
            "mcnemar_p_one_sided": round(binom_tail(len(wins), n), 4),
            "mcnemar_p_two_sided": round(min(1.0, 2 * binom_tail(max(len(wins), len(losses)),
                                                                  n)), 4),
            "y_token_f1": {"base": f1(base, y), "variant": f1(variant, y), "tasks": len(y)},
            "y_token_f1_both_answered": {"base": f1(base, both), "variant": f1(variant, both),
                                         "tasks": len(both)},
            "win_tasks": wins, "loss_tasks": losses}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("base", nargs="?")
    parser.add_argument("variant", nargs="?")
    parser.add_argument("--system", default="multi")
    parser.add_argument("--retro", action="store_true")
    args = parser.parse_args()
    if args.retro:
        report = {r: [compare(b, v) for v in vs] for r, (b, vs) in RETRO.items()}
        out = RESULTS / "paired_retro.json"
        out.write_text(json.dumps(report, indent=1) + "\n", encoding="utf-8")
        for r, items in report.items():
            for c in items:
                print(r, c["variant"], f"{c['base_correct']}->{c['variant_correct']}",
                      f"+{c['wins']}/-{c['losses']}", c["mcnemar_p_two_sided"],
                      c["y_token_f1"]["base"], c["y_token_f1"]["variant"])
        return
    print(json.dumps(compare(args.base, args.variant, args.system), indent=1))


if __name__ == "__main__":
    main()
