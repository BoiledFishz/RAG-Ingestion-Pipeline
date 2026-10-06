"""Question-cluster confidence intervals; repeated observations are not new questions."""

from __future__ import annotations

import math
import random
from collections import defaultdict
from statistics import mean
from typing import Any


def wilson(successes: int, total: int) -> list[float] | None:
    if not total:
        return None
    z = 1.959963984540054
    p = successes / total
    denominator = 1 + z * z / total
    center = (p + z * z / (2 * total)) / denominator
    half = z * math.sqrt(p * (1 - p) / total + z * z / (4 * total * total))
    return [max(0.0, center - half / denominator), min(1.0, center + half / denominator)]


def metric(
    rows: list[dict[str, Any]], key: str, *, binary: bool = False, resamples: int = 2000
) -> dict[str, Any]:
    usable = [row for row in rows if row.get(key) is not None]
    repeats: dict[int, list[dict[str, Any]]] = defaultdict(list)
    clusters: dict[str, list[float]] = defaultdict(list)
    for row in usable:
        repeats[row["repeat"]].append(row)
        clusters[row["group_sha256"]].append(float(row[key]))
    per_repeat = []
    for repeat, observations in sorted(repeats.items()):
        values = [float(row[key]) for row in observations]
        item: dict[str, Any] = {
            "repeat": repeat,
            "numerator": sum(values),
            "denominator": len(values),
            "value": mean(values),
        }
        # Wilson is valid for these quick sets: one query group per row.
        if binary and len({r["group_sha256"] for r in observations}) == len(values):
            item["ci95"] = wilson(int(sum(values)), len(values))
            item["ci_method"] = "Wilson, independent query groups within repeat"
        per_repeat.append(item)
    if not usable:
        return {
            "mean": None,
            "range": None,
            "numerator": 0,
            "denominator": 0,
            "independent_query_groups": 0,
            "ci95": None,
            "interpretation": "仅描述，不作结论",
            "reason": "no eligible observations",
        }
    # Sample whole groups, retaining their repeats and official duplicate records.
    samples = list(clusters.values())
    rng = random.Random(20261004)
    boot = []
    for _ in range(resamples):
        selected = [samples[rng.randrange(len(samples))] for _ in samples]
        boot.append(sum(sum(v) for v in selected) / sum(len(v) for v in selected))
    boot.sort()
    values = [r["value"] for r in per_repeat]
    interval = [boot[int(0.025 * resamples)], boot[int(0.975 * resamples) - 1]]
    method = "percentile bootstrap of whole query groups; 2000 draws, fixed seed"
    if binary and all("ci95" in r for r in per_repeat):
        interval = [min(r["ci95"][0] for r in per_repeat), max(r["ci95"][1] for r in per_repeat)]
        method = "conservative envelope of per-repeat Wilson intervals; never pool repeat n"
    return {
        "mean": mean(values),
        "range": [min(values), max(values)],
        "numerator": sum(float(row[key]) for row in usable),
        "denominator": len(usable),
        "independent_query_groups": len(clusters),
        "ci95": interval,
        "ci_method": method,
        "per_repeat": per_repeat,
        "interpretation": "仅描述，不作结论" if len(clusters) < 10 else "estimate with CI",
        "repeated_runs_are_independent_questions": False,
    }
