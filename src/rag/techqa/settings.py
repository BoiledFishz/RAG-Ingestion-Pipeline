"""Training-only relevance calibration shared by all serving adapters."""

from __future__ import annotations

import json
import os
from functools import lru_cache

from rag.techqa.data import ROOT


@lru_cache(maxsize=1)
def thresholds() -> dict[str, float]:
    data = json.loads((ROOT / "config/techqa_thresholds.json").read_text(encoding="utf-8"))
    return {name: float(row["threshold"]) for name, row in data["thresholds"].items()}


def relevance_threshold(mode: str = "hybrid") -> float:
    if os.getenv("TECHQA_PROFILE") == "fixture":
        return 0.0
    default = thresholds()["dense_rerank" if mode == "dense" else "hybrid_rerank"]
    return float(os.getenv("TECHQA_RELEVANCE_THRESHOLD", str(default)))


def acceptance_score(
    query: str, text: str, score: float, *, fallback: bool = False, mode: str = "hybrid"
) -> tuple[float, float]:
    if fallback:
        from rag.techqa.retrieval import coverage

        return coverage(query, text), float(os.getenv("TECHQA_FALLBACK_THRESHOLD", "0.5"))
    return score, relevance_threshold(mode)
