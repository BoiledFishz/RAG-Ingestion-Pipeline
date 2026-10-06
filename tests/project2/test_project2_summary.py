"""Reporting must distinguish a numerical failure from a claimed pass."""

import copy
import json
from pathlib import Path

from scripts.summarize_project2 import stage_verdict, revision_details, latest_native_gate


ROOT = Path(__file__).resolve().parents[2]


def load_report() -> dict:
    return json.loads((ROOT / "audit/project2-v1/spec_preflight.json").read_text(encoding="utf-8"))


def test_claimed_pass_does_not_override_independent_count_failure() -> None:
    report = copy.deepcopy(load_report())
    report["status"] = "passed"
    assert stage_verdict(report) == "failed"


def test_preflight_pass_does_not_mean_full_stage_pass() -> None:
    # Fault-injection on report metadata only; not generated TechQA content.
    report = copy.deepcopy(load_report())
    report["status"] = "passed"
    for check in report["checks"]:
        check["actual_count"] = check["expected_count"]
        check["status"] = "passed"
    report["system_gate_executed"] = False
    assert stage_verdict(report) == "not_executed"


def test_revision_count_comes_from_checked_delta() -> None:
    details = revision_details(ROOT)
    assert details["version"] == "v0.2"
    assert details["delta_count"] == len(details["changes"]) == 2
    assert details["v01_unchanged"] is True


def test_latest_native_failure_is_not_hidden_by_data_preflight() -> None:
    report, filename = latest_native_gate(ROOT / "audit/project2-v1")
    assert report["repair_rounds"] == 2
    assert filename == "native_gate_round2.json"
    assert stage_verdict(report) == "failed"
