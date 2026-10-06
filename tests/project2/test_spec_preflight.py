"""Frozen scenario expectations must agree with the official full corpus.

These tests use original preregistered query text and read-only real SQLite.
No answer, Y/N label, target document or synthetic document is loaded.
"""

from pathlib import Path

from scripts.project2_spec_preflight import verify_registered_zero_case


ROOT = Path(__file__).resolve().parents[2]


def test_registered_real_zero_count_is_zero() -> None:
    result = verify_registered_zero_case(ROOT)
    assert result["status"] == "passed", (
        "Approved AC12-02 requires a complete zero-match count. "
        f"Independent official full-corpus count={result['actual_count']}; "
        f"predicate={result['predicate']!r}. "
        "Do not alter the frozen query, predicate, corpus or expected state."
    )
