"""P1-2: split the v1 -> v2 change of Multi-Agent `failed` (44 -> 0) into its two causes.

    python -m evaluation.chap12_failed_decomposition
Reads only the committed offline runs of v1 and v2 (same 150 tasks, same order)."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

RESULTS = Path(__file__).resolve().parent / "chap12/results"


def load(name: str) -> dict[str, dict[str, object]]:
    rows = [json.loads(x) for x in (RESULTS / name / "runs.jsonl").read_text("utf-8").splitlines()]
    return {str(r["task_id"]): r for r in rows if r["system"] == "multi_agent"}


def main() -> None:
    v1, v2 = load("offline_20261011"), load("offline_v2_20261011")
    failed = [t for t, r in v1.items() if r["status"] == "failed"]
    causes: Counter[str] = Counter()
    for task in failed:
        after = v2[task]
        if after.get("data_product_source") == "inferred" and after["data_status"] == "completed":
            causes["product_inference_rescue (data completed via inferred product)"] += 1
        elif after["data_status"] == "no_data":
            causes["reclassified (missing product: failed -> no_data/clarification)"] += 1
        else:
            causes[f"other (v2 data_status={after['data_status']})"] += 1
    report = {"v1_failed": len(failed), "v2_failed": sum(r["status"] == "failed"
                                                         for r in v2.values()),
              "causes": dict(causes),
              "v2_overall_status_of_v1_failed": dict(Counter(str(v2[t]["status"])
                                                             for t in failed))}
    (RESULTS / "v1_v2_failed_decomposition.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=1) + "\n", "utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
