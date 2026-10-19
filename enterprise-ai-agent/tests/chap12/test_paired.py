"""Round 5: paired comparison (exact McNemar) and token F1 reporting."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from evaluation import chap12_paired
from evaluation.chap12_paired import binom_tail, compare


def write(root: Path, name: str, correct: list[bool], published: list[bool]) -> None:
    (root / name).mkdir()
    rows = [{"system": "multi", "task_id": f"T{i}", "repeat": 1, "published": p,
             "score": {"answerable": True, "correct": c, "token_f1": 0.5 if p else 0.0}}
            for i, (c, p) in enumerate(zip(correct, published, strict=True))]
    (root / name / "runs.jsonl").write_text("\n".join(json.dumps(r) for r in rows))


def test_binomial_tail() -> None:
    assert binom_tail(0, 4) == 1.0 and binom_tail(4, 4) == 1 / 16
    assert binom_tail(0, 0) == 1.0


def test_compare_counts_discordant_pairs(tmp_path: Path,
                                         monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(chap12_paired, "RESULTS", tmp_path)
    write(tmp_path, "a", [True, False, False, False, True], [True] * 5)
    write(tmp_path, "b", [True, True, True, True, False], [True, True, True, True, False])
    c = compare("a", "b")
    assert (c["wins"], c["losses"], c["net"]) == (3, 1, 2)
    assert c["mcnemar_p_one_sided"] == round(5 / 16, 4)
    assert c["y_token_f1"] == {"base": 0.5, "variant": 0.4, "tasks": 5}
    assert c["y_token_f1_both_answered"]["tasks"] == 4


def test_compare_refuses_different_task_sets(tmp_path: Path,
                                             monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(chap12_paired, "RESULTS", tmp_path)
    write(tmp_path, "a", [True, False], [True, True])
    write(tmp_path, "b", [True], [True])
    with pytest.raises(ValueError):
        compare("a", "b")
