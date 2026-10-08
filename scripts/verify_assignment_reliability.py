"""Chap15 actual SQLite/cache/model faults; no fabricated QA or gold online."""

from __future__ import annotations

import asyncio
import hashlib
import importlib.util
import json
import logging
import sqlite3
import sys
from contextlib import closing
from pathlib import Path
from types import SimpleNamespace
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "src"), str(ROOT / "enterprise-ai-agent")]
AUDIT = ROOT / "audit/assignment-completion-20261007"


async def verify() -> dict[str, Any]:
    from agents.project2.batched_retrieval import BatchedReranker
    from agents.project2.budget import Budget, BudgetExceeded
    from agents.project2.cache_identity import authorization_scope, cache_context
    from agents.project2.policy import TrustedContext
    from agents.project2.rag_process import BudgetConnection
    from models.project2 import AnalysisRequest
    from tools.techqa_document_query import DatabaseWorker, query_groups

    folder = AUDIT / "reliability_fault"
    folder.mkdir(exist_ok=False)
    checks = []

    def check(name: str, observed: bool, kind: str, detail: Any) -> None:
        checks.append(
            {
                "check": name,
                "observed": bool(observed),
                "expected": True,
                "status": "passed" if observed else "failed",
                "evidence_type": kind,
                "detail": detail,
            }
        )
        (folder / "checks.partial.json").write_text(
            json.dumps(checks, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    corpus = ROOT / ".rag_data/techqa_full.sqlite"
    with closing(sqlite3.connect(corpus.resolve().as_uri() + "?mode=ro", uri=True)) as db:
        text = (
            "search_document: "
            + db.execute("SELECT text FROM docs ORDER BY doc_id LIMIT 1").fetchone()[0][:512]
        )
        manifest = dict(db.execute("SELECT key,value FROM manifest"))
    version = hashlib.sha256(json.dumps(manifest, sort_keys=True).encode()).hexdigest()
    owner = TrustedContext(
        "fault-evaluator",
        "local",
        frozenset({"full"}),
        frozenset({"document_count", "compare_document_counts", "rag_explain"}),
    )
    other = TrustedContext(
        "fault-evaluator", "other-tenant", frozenset({"full"}), frozenset({"rag_explain"})
    )

    # Preserve and execute the actual pre-change cache implementation, not a
    # replacement function that merely mirrors the desired implementation.
    source = AUDIT / "reliability_before/source_snapshot/batched_retrieval.py"
    before_plan = json.loads((AUDIT / "reliability_before/plan.json").read_text(encoding="utf-8"))
    expected = before_plan["online_sources"][
        "enterprise-ai-agent/agents/project2/batched_retrieval.py"
    ]
    if hashlib.sha256(source.read_bytes()).hexdigest() != expected:
        raise ValueError("Before source snapshot differs from registered source")
    spec = importlib.util.spec_from_file_location("assignment_before_cache", source)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    before = module.BatchedReranker(True)
    after = BatchedReranker(True)
    before.cache = after.cache = folder / "injected_cache.sqlite"
    legacy_key = hashlib.sha256((before.embedder.model + ":v1:" + text).encode()).hexdigest()
    with closing(sqlite3.connect(before.cache)) as db:
        db.execute("CREATE TABLE embeddings(key TEXT PRIMARY KEY,vector TEXT)")
        db.execute("INSERT INTO embeddings VALUES (?,?)", (legacy_key, json.dumps([0.0] * 768)))
        db.commit()
    stale = await before.embeddings([text])
    check(
        "injected_stale_legacy_entry_reproduced",
        stale == [[0.0] * 768],
        "故障注入",
        {
            "stage": "reranker.embedding_cache",
            "root_cause": "legacy key contains model/text only; no data or permission version",
            "before_source_sha256": expected,
            "corpus_or_qa_changed": False,
        },
    )
    original = after.embedder.embed_documents
    calls = []

    async def observed(texts: list[str]) -> list[list[float]]:
        calls.append(len(texts))
        return await original(texts)

    # The real provider is a slotted dataclass. A transparent observer delegates
    # to its actual HTTP method; it does not supply substitute vectors.
    after.embedder = SimpleNamespace(model=after.embedder.model, embed_documents=observed)
    with cache_context(version, authorization_scope(owner)):
        fresh = await after.embeddings([text])
        cached = await after.embeddings([text])
    check(
        "stale_entry_bypassed_and_actual_model_recovered",
        fresh == cached and any(fresh[0]),
        "故障注入",
        {
            "same_text_sha256": hashlib.sha256(text.encode()).hexdigest(),
            "actual_http_embedding_calls": len(calls),
            "vector_dimension": len(fresh[0]),
            "same_condition_retest": True,
        },
    )
    with cache_context(version, authorization_scope(other)):
        tenant_result = await after.embeddings([text])
    with cache_context(version + ":fault-version-change", authorization_scope(owner)):
        version_result = await after.embeddings([text])
    check(
        "cache_authorization_and_version_isolation",
        len(calls) == 3
        and all(abs(a - b) < 1e-5 for a, b in zip(fresh[0], tenant_result[0], strict=True))
        and all(abs(a - b) < 1e-5 for a, b in zip(fresh[0], version_result[0], strict=True)),
        "真实运行",
        {
            "actual_embedding_calls": len(calls),
            "changed_metadata_is_fault_injection": True,
            "same_scope_hit": True,
            "model": after.embedder.model,
            "data_version": version,
        },
    )

    budget = Budget()
    with closing(
        sqlite3.connect(corpus.resolve().as_uri() + "?mode=ro", uri=True, factory=BudgetConnection)
    ) as db:
        db.request_budget = budget
        for _ in range(budget.max_attempts):
            db.execute("SELECT value FROM manifest WHERE key='scope'").fetchone()
        denied = False
        try:
            db.execute("SELECT value FROM manifest WHERE key='scope'")
        except BudgetExceeded:
            denied = True
    check(
        "dependency_N_plus_1_not_started",
        denied and budget.attempts == 19,
        "故障注入",
        budget.snapshot(),
    )

    samples = json.loads(
        (ROOT / "evals/project2-v1/calibration_v031/protocol.json").read_text(encoding="utf-8")
    )["samples"]
    sample = next(
        s
        for s in samples
        if s["analysis_operation"] == "compare_document_counts"
        and len(
            query_groups(
                AnalysisRequest(query=s["query"], analysis_operation=s["analysis_operation"])
            )
        )
        == 2
    )
    request = AnalysisRequest(
        query=sample["query"], analysis_operation=sample["analysis_operation"]
    )
    worker = DatabaseWorker(corpus, inject_timeout_group=1)
    result = await worker.run(request, owner, Budget(), "fault-readonly")
    groups = result.payload.get("groups", [])
    check(
        "real_database_partial_preserves_null_not_zero",
        result.status == "partial"
        and len(groups) == 2
        and groups[0]["count"] is not None
        and groups[1]["count"] is None,
        "故障注入",
        result.model_dump(mode="json"),
    )
    return {
        "stage": "Chap15",
        "status": "passed" if all(c["observed"] for c in checks) else "failed",
        "system_gate_executed": True,
        "checks": checks,
        "failure_items": [c["check"] for c in checks if not c["observed"]],
        "heldout_new_calls": 0,
        "corpus_and_official_qa_unchanged": True,
        "scope": "existing dependency only; no result cache, circuit breaker or new retry",
        "fault_lifecycle": (
            "discover stale cache -> source/SQLite trace diagnosis -> "
            "namespace fix -> identical injected entry retest"
        ),
    }


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    result = asyncio.run(verify())
    (AUDIT / "reliability_fault/gate.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    raise SystemExit(int(result["status"] != "passed"))
