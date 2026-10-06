"""Run registered real Project 2 combined probes, never an evaluation rerun.

Uses approved tune original query text. No gold/target/label enters a Worker.
Gate conditions are frozen before the first run; failures are not relabelled.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def run_gate(root: Path, *, repair_round: int) -> dict[str, Any]:
    if not 0 <= repair_round <= 2:
        raise ValueError("At most two repair rounds; do not rerun after that limit")
    target = root / "audit/project2-v1" / f"native_gate_round{repair_round}.json"
    if target.is_file():
        raise ValueError(f"Native gate round{repair_round} already recorded; refusing execution/overwrite")
    sys.path.insert(0, str(root / "enterprise-ai-agent"))
    from api.project2_main import create_app
    from agents.project2.policy import TrustedContext
    from fastapi.testclient import TestClient

    docs = root / "specs/project2/v0.2"
    with (docs / "acceptance_scenarios.csv").open(encoding="utf-8-sig", newline="") as handle:
        cases = {x["scenario_id"]: x for x in csv.DictReader(handle)}
    selected = [cases[key] for key in ("AC12-01", "AC12-23")]
    protocol = {"version": "project2-native-combination-v1", "partition": "tune", "scenarios": [{"scenario_id": x["scenario_id"], "input": json.loads(x["input_source_and_selection"]), "expected_worker_states": x["expected_worker_states"], "expected_overall_status": x["expected_overall_status"]} for x in selected], "max_repair_rounds": 2, "prompt": "frozen baseline v0", "dependency_limit": 16, "llm_limit": 6, "timeout_seconds": 90}
    audit = root / "audit/project2-v1"
    registered = audit / "native_gate_registration.json"
    payload = json.dumps(protocol, ensure_ascii=False, indent=2) + "\n"
    if registered.is_file() and registered.read_text(encoding="utf-8") != payload:
        raise ValueError("Native gate preregistration changed; refusing execution")
    if not registered.is_file():
        registered.write_text(payload, encoding="utf-8")
    results = []
    credential = "local-gate-only"
    owner = TrustedContext("gate-owner", "local", frozenset({"full"}), frozenset({"document_count", "compare_document_counts", "list_matching_documents", "rag_explain"}))
    app = create_app(credentials={credential: owner}, warmup=True)
    try:
        with TestClient(app) as client:
            ready = client.get("/healthz").json()
            for case in selected:
                body = json.loads(case["input_source_and_selection"])
                body.pop("sample_id")
                started = time.monotonic()
                output = client.post("/v1/project2/analysis", headers={"Authorization": f"Bearer {credential}"}, json=body)
                data = output.json()
                observed_pair = f"RAG={data['workers']['rag']['status']};DB={data['workers']['database']['status']}"
                results.append({"check": case["scenario_id"], "scenario_id": case["scenario_id"],
                                "expected": {"worker_states": case["expected_worker_states"], "overall": case["expected_overall_status"]},
                                "observed": {"worker_states": observed_pair, "overall": data["status"]},
                                "status": "passed" if observed_pair == case["expected_worker_states"] and data["status"] == case["expected_overall_status"] else "failed",
                                "http_status": output.status_code, "result": data, "elapsed_ms": (time.monotonic()-started)*1000,
                                "evidence_type": "真实运行", "transport": "in-process ASGI HTTP; native separate model/FAISS process"})
    except Exception as exc:
        results.append({"check": "native_dependencies_ready", "expected": "ready", "observed": type(exc).__name__+":"+str(exc), "status": "failed", "evidence_type": "真实运行", "evidence_scope": "actual_startup_attempt_only"})
    report = {"schema_version": 1, "stage": "Chap12", "gate_scope": "native_combination_subgate", "system_gate_executed": False,
              "generated_at": datetime.now(timezone.utc).isoformat(), "status": "passed" if all(x["status"] == "passed" for x in results) and len(results) == 2 else "failed",
              "checks": results, "failure_items": [x["check"] for x in results if x["status"] != "passed"],
              "repair_rounds": repair_round, "registration_sha256": hashlib.sha256(registered.read_bytes()).hexdigest(),
              "heldout_stage_calls_project2": 0, "heldout_repetitions_project2": 0,
              "not_completed_stage_gate": True, "not_quality_evaluation": True}
    target.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repair-round", type=int, required=True)
    args = parser.parse_args()
    report = run_gate(Path(__file__).resolve().parents[1], repair_round=args.repair_round)
    sys.stdout.write(json.dumps({"status": report["status"], "failure_items": report["failure_items"], "repair_round": report["repair_rounds"]}, ensure_ascii=False) + "\n")
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    raise SystemExit(main())
