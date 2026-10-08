"""Correct saved observer classifications without rerunning inference."""

from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from evaluation_protocol.statistics import metric  # noqa: E402


def correct() -> dict:
    folder = ROOT / "audit/assignment-completion-20261007/chap11"
    raw_path = folder / "requests.jsonl"
    raw_summary = folder / "summary.json"
    output = folder / "requests.corrected.jsonl"
    summary_output = folder / "summary.corrected.json"
    if output.exists() or summary_output.exists():
        raise FileExistsError("Never overwrite a measurement correction")
    rows = [json.loads(line) for line in raw_path.read_text(encoding="utf-8").splitlines()]
    value = json.loads(raw_summary.read_text(encoding="utf-8"))
    if len(rows) != 234 or value["requests"] != len(rows):
        raise ValueError("Comparison incomplete; do not correct partial results")
    urls = re.findall(
        r'HTTP Request: POST (\S+) "', (folder.parent / "chap11.log").read_text(encoding="utf-8")
    )
    paths = sorted({urlparse(url).path for url in urls})
    if not urls or any(urlparse(url).hostname not in {"localhost", "127.0.0.1"} for url in urls):
        raise ValueError("Unexpected provider contract")
    if not set(paths) <= {"/api/chat", "/api/generate", "/api/embed"}:
        raise ValueError("Generic HTTP count cannot be safely attributed")
    generator = ROOT / "src/rag/generation/generator.py"
    if '"/api/generate"' not in generator.read_text(encoding="utf-8"):
        raise ValueError("Original generator adapter contract changed")
    status_counts: dict[str, int] = {}
    for row in rows:
        if row["system"] == "agentic_rag":
            status = row.get("result", {}).get("trace", {}).get("status")
            if status not in {
                "answered",
                "partial",
                "clarified",
                "unanswerable",
                "invalid_evidence",
                None,
            }:
                raise ValueError("Unknown saved Agent status: " + str(status))
            status_counts[str(status)] = status_counts.get(str(status), 0) + 1
            row["n_refusal_raw"] = row["n_refusal"]
            row["citation_valid_raw"] = row["citation_valid"]
            row["output_validation_failure"] = int(status == "invalid_evidence")
            refused = status == "unanswerable" and row["error"] is None
            if row["n_refusal"] is not None:
                row["n_refusal"] = int(refused)
            if refused:
                response = row["result"]["response"]
                if response.get("sources") or response.get("confidence") != 0:
                    raise ValueError("Unanswerable response violates the frozen refusal contract")
                row["citation_valid"] = None
        if row["system"] != "original_rag":
            continue
        row["n_refusal_raw"] = row["n_refusal"]
        row["citation_valid_raw"] = row["citation_valid"]
        reason = row.get("result", {}).get("refusal_reason")
        if reason not in {
            "no_retrieval_results",
            "below_relevance_threshold",
            "empty_context",
            "invalid_citation",
            None,
        }:
            raise ValueError("Unknown original refusal reason: " + str(reason))
        row["output_validation_failure"] = int(reason == "invalid_citation")
        if reason == "invalid_citation":
            if row["n_refusal"] is not None:
                row["n_refusal"] = 0
            row["citation_valid"] = 0
        if row["llm_calls"] != 0:
            raise ValueError("This correction applies only to the registered defective observer")
        row["llm_calls_raw"] = row["llm_calls"]
        row["llm_calls"] = row["calls"] - row["embedding_calls"]
        if row["llm_calls"] < 0:
            raise ValueError("Inconsistent saved HTTP counters")
        row["observed_tokens"] = None
        row["token_scope"] = "Generator usage not captured; do not infer a total"
    output.write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8"
    )
    for system, metrics in value["systems"].items():
        selected = [row for row in rows if row["system"] == system]
        metrics["output_validation_failure"] = None
        for key in metrics:
            metrics[key] = metric(
                selected,
                key,
                binary=key
                in {
                    "worker_failure",
                    "citation_valid",
                    "n_refusal",
                    "target_cited",
                    "retrieval_recall5",
                    "output_validation_failure",
                },
            )
    for system, kinds in value["by_type"].items():
        for kind, metrics in kinds.items():
            selected = [
                row for row in rows if row["system"] == system and row["question_type"] == kind
            ]
            metrics["output_validation_failure"] = None
            for key in metrics:
                metrics[key] = metric(
                    selected,
                    key,
                    binary=key
                    in {
                        "worker_failure",
                        "citation_valid",
                        "n_refusal",
                        "retrieval_recall5",
                        "output_validation_failure",
                    },
                )
    value["measurement_correction"] = {
        "raw_records_sha256": hashlib.sha256(raw_path.read_bytes()).hexdigest(),
        "raw_summary_sha256": hashlib.sha256(raw_summary.read_bytes()).hexdigest(),
        "corrected_records_sha256": hashlib.sha256(output.read_bytes()).hexdigest(),
        "generator_source_sha256": hashlib.sha256(generator.read_bytes()).hexdigest(),
        "observed_paths": paths,
        "rule": "original LLM attempts = saved total HTTP attempts - embedding attempts",
        "original_generator_tokens": "unknown; not recoverable from retained observation",
        "agent_refusal_rule": (
            "trace.status=unanswerable and no exception; clarified/invalid_evidence/partial "
            "are not successful N refusals; citations are inapplicable for valid refusals"
        ),
        "agent_status_counts": status_counts,
        "original_refusal_rule": (
            "invalid_citation is an output validation failure, not successful knowledge "
            "refusal; n_refusal=0 and citation_valid=0, preserved raw values"
        ),
        "agent_schema_sha256": hashlib.sha256(
            (ROOT / "enterprise-ai-agent/models/schemas.py").read_bytes()
        ).hexdigest(),
        "agent_service_sha256": hashlib.sha256(
            (ROOT / "enterprise-ai-agent/agents/rag_agent/service.py").read_bytes()
        ).hexdigest(),
        "models_rerun": 0,
        "answer_body_f1_retrieval_scores_answers_queries_unchanged": True,
        "changed_metrics": [
            "original llm_calls",
            "n_refusal",
            "citation_valid",
            "output_validation_failure",
        ],
    }
    value["token_scope"] = (
        "Agentic observed completed-response Ollama usage; original generation usage "
        "was not captured. Original token total remains unknown; raw embedding-only "
        "usage is retained in the raw records. No local monetary price is invented."
    )
    summary_output.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return value


if __name__ == "__main__":
    report = correct()
    print(json.dumps(report["measurement_correction"], ensure_ascii=False, indent=2))
