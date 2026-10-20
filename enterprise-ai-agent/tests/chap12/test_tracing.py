"""Layer trace (2026-10-20): recorder is opt-in, and attribution picks the first failing layer."""

from __future__ import annotations

from typing import Any

import pytest

from agents.chap12 import tracing
from evaluation.chap12_trace_report import attribute


def test_record_is_noop_without_recorder() -> None:
    tracing.record("x", 1)  # must not raise
    assert tracing.active() is None
    with tracing.recording() as data:
        tracing.record("x", 1)
    assert data == {"x": 1} and tracing.active() is None


def row(stages: dict[str, list[str]], returned: list[str], evidence: list[str],
        cited: list[str], published: bool = True, **score: Any) -> dict[str, Any]:
    def ranked(ds: list[str]) -> list[dict[str, Any]]:
        return [{"doc": d, "rank": i, "score": 0.5} for i, d in enumerate(ds, 1)]

    return {"task_id": "T", "type": "explain", "published": published,
            "score": {"answerable": True, "correct": False} | score,
            "layers": {"retrieval": {"stages": {k: ranked(v) for k, v in stages.items()},
                                     "returned": [{"doc": d, "score": 0.6, "threshold": 0.65}
                                                  for d in returned]},
                       "rag": {"evidence": [{"doc": d} for d in evidence], "cited": cited}}}


GOLD = {"document": "G"}
ALL = {"dense": ["G", "a"], "sparse": ["a"], "fusion": ["a", "G"], "rerank": ["a", "G"]}


@pytest.mark.parametrize(("r", "layer"), [
    (row({"dense": ["a"], "sparse": ["b"], "fusion": ["a"], "rerank": ["a"]}, ["a"], [], []),
     "L1 retrieval: not retrieved"),
    (row({"dense": ["G"], "sparse": [], "fusion": ["a"], "rerank": ["a"]}, ["a"], [], []),
     "L1 retrieval: fusion cut"),
    (row(ALL, ["a"], ["a"], ["a"]), "L2 rerank"),
    (row(ALL, ["a", "G"], ["a"], ["a"]), "L3 context"),
    (row(ALL, ["a", "G"], ["a", "G"], ["a"]), "L4 generation: cited other"),
    (row(ALL, ["a", "G"], ["a", "G"], []), "L4 generation: refused"),
    (row(ALL, ["G"], ["G"], ["G"], published=False), "L5 supervisor: withheld"),
    (row(ALL, ["G"], ["G"], ["G"], correct=True), "correct"),
])
def test_first_failing_layer(r: dict[str, Any], layer: str) -> None:
    assert attribute(r, GOLD)["layer"] == layer


def test_unanswerable_answered_is_a_refusal_failure() -> None:
    r = row(ALL, ["a"], ["a"], ["a"], answerable=False, rag_correct=False)
    assert attribute(r, GOLD)["layer"] == "L4 refusal: answered unanswerable"
