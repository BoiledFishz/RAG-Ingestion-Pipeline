"""Read-only validation of frozen TechQA scenario prerequisites.

This is an independent specification/data check, not an online Worker or an
evaluation scorer. Query construction uses only preregistered query text/rules.
It must stop execution on contradiction rather than repair approved documents.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import sqlite3
import sys
import time
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_registered_zero_case(root: Path, version: str = "v0.3.4") -> dict[str, Any]:
    """Check AC12-02's frozen DB=no_data expectation using exact FTS COUNT."""
    baseline_docs = root / "specs/project2/v0.1"
    docs = root / "specs/project2" / version
    if version not in {"v0.1", "v0.2", "v0.3", "v0.3.1", "v0.3.2", "v0.3.3", "v0.3.4"}:
        raise ValueError("Unknown approved specification version")
    if version != "v0.1":
        import importlib.util
        loader = importlib.util.spec_from_file_location("zero_case_approved_checker", docs / "check_docs.py")
        checker = importlib.util.module_from_spec(loader)
        loader.loader.exec_module(checker)
        checker.validate(docs, root)
    signed = (baseline_docs / "review_sheet_signed_2026-10-05.md").read_text(encoding="utf-8-sig")
    hashes = re.findall(r"(?<![0-9a-f])[0-9a-f]{64}(?![0-9a-f])", signed)
    approved_files = ("requirements_v0.1.md", "task_preregistration.json")
    if len(hashes) != len(approved_files):
        raise ValueError("Signed baseline hash list is not unambiguous")
    if any(digest(baseline_docs / name) != expected for name, expected in zip(approved_files, hashes)):
        raise ValueError("Approved baseline hash mismatch")
    with (docs / "acceptance_scenarios.csv").open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    scenario = next(row for row in rows if row["scenario_id"] == "AC12-02")
    if scenario["expected_worker_states"] != "RAG=completed;DB=no_data":
        raise ValueError("Frozen AC12-02 expected Worker states differ")
    registration = json.loads((docs / "task_preregistration.json").read_text(encoding="utf-8"))
    sample = next(row for row in registration["samples"] if row["sample_id"] == scenario["input_sample_id"])
    request = json.loads(scenario["input_source_and_selection"])
    if request["query"] != sample["query"] or request["analysis_operation"] != "document_count":
        raise ValueError("Frozen original query or operation differs")

    # S01: first explicit entity in title and its adjacent literal version.
    # No target ID, answer or official Y/N label is read or consulted.
    rules = registration["sampling_rules"]
    flags = re.ASCII | re.IGNORECASE
    entity = re.search(rules["entity_pattern"], sample["original_question_title"], flags)
    if entity is None:
        raise ValueError("Prerequisite needs an explicit entity in the original title")
    title = sample["original_question_title"]
    tail = title[entity.end():entity.end() + 32]
    version = re.search(rules["version_pattern"], tail, flags)
    if version is None:
        raise ValueError("Prerequisite needs an unambiguous adjacent version")
    literals = [entity.group(), version.group()]
    if request.get("analysis_predicates") is not None:
        registration_zero = json.loads((docs / "zero_predicate_registration.json").read_text(encoding="utf-8"))
        literals = request["analysis_predicates"][0]
        if not any(item["phrases"] == literals and item["count"] == 0 for item in registration_zero["predicates"]):
            raise ValueError("Literal zero predicate is not independently registered")
    expression = " AND ".join('"' + phrase.replace('"', '""') + '"' for phrase in literals)

    database = (root / ".rag_data/techqa_full.sqlite").resolve()
    if not database.is_file():
        raise FileNotFoundError("Official full-corpus index is unavailable")
    started = time.perf_counter()
    with closing(sqlite3.connect(database.as_uri() + "?mode=ro", uri=True, timeout=12)) as db:
        manifest = dict(db.execute("SELECT key,value FROM manifest"))
        schema = db.execute("SELECT sql FROM sqlite_master WHERE name='search'").fetchone()
        spec = (docs / "spec.md").read_text(encoding="utf-8-sig")
        if manifest.get("complete") != "true" or manifest.get("scope") != "full":
            raise ValueError("Incomplete or non-full corpus cannot validate the scenario")
        if manifest.get("format_version") != "1":
            raise ValueError("Unexpected corpus schema version")
        if manifest.get("source_archive_sha256") not in spec:
            raise ValueError("Corpus provenance is not the approved archive")
        if not schema or "tokenize='porter unicode61'" not in schema[0]:
            raise ValueError("FTS tokenizer differs from the approved predicate rule")
        db.set_progress_handler(lambda: int(time.perf_counter() - started >= 25), 1000)
        actual_count = db.execute(
            "SELECT COUNT(DISTINCT d.doc_id) FROM docs AS d "
            "JOIN search ON search.rowid=d.rowid WHERE search MATCH ?", (expression,)
        ).fetchone()[0]
    return {
        "check": "frozen_real_zero_count", "scenario_id": scenario["scenario_id"],
        "sample_id": sample["sample_id"], "query_sha256": sample["query_sha256"],
        "input_fields": ["original_question_title", "original_question_text"],
        "predicate": literals, "fts_expression": expression,
        "expected_count": 0, "actual_count": actual_count,
        "measurement_complete": True, "elapsed_ms": (time.perf_counter()-started)*1000,
        "database": ".rag_data/techqa_full.sqlite", "manifest": manifest,
        "evidence_type": "真实运行", "evidence_scope": "independent_read_only_database_recount_only",
        "status": "passed" if actual_count == 0 else "failed",
        "failure_kind": None if actual_count == 0 else "approved_specification_data_contradiction",
        "not_worker_execution": True, "llm_calls": 0,
        "heldout_stage_calls_project2": 0,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    root = args.root.resolve()
    audit = root / "audit/project2-v1"
    audit.mkdir(parents=True, exist_ok=True)
    try:
        check = verify_registered_zero_case(root)
    except (ValueError, OSError, sqlite3.Error, StopIteration) as error:
        check = {"check": "frozen_real_zero_count", "status": "failed", "failure_kind": "prerequisite_unavailable", "error": str(error), "evidence_type": "未执行", "not_worker_execution": True}
    report = {
        "schema_version": 1, "stage": "Chap12", "gate_scope": "approved_specification_preflight",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": check["status"], "checks": [check],
        "repair_rounds": 0, "system_gate_executed": False,
        "heldout_stage_calls_project2": 0, "heldout_repetitions_project2": 0,
    }
    output = audit / "spec_preflight.json"
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    sys.stdout.write(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    raise SystemExit(main())
