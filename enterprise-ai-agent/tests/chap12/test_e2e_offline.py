"""Real committed TechQA documents, real Supervisor/DB Worker/Project 1 RAG agent.

Offline profile: rule rewrite + extractive selection, lexical rerank, no model service.
"""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from agents.chap12.contracts import AnalysisRequest
from agents.chap12.factory import build_supervisor
from models.settings import Settings
from tests.chap12.conftest import context

QUESTION = (
    "User environment variables no longer getting picked up after upgrade to 4.1.1.1 or 4.1.1.2?"
    "\nHave you found that after upgrade to Streams 4.1.1.1 or 4.1.1.2, that environment "
    "variables set in your .bashrc are no longer being set?")


@pytest.fixture
def supervisor(sample_index: Path, monkeypatch: pytest.MonkeyPatch):  # type: ignore[no-untyped-def]
    monkeypatch.setenv("TECHQA_PROFILE", "fixture")  # calibrated thresholds do not apply here
    return build_supervisor(Settings(profile="offline"), sample_index)


def test_combined_request_runs_both_real_workers(supervisor) -> None:  # type: ignore[no-untyped-def]
    result = asyncio.run(supervisor.run(AnalysisRequest(query=QUESTION), context()))
    rag, db = result.worker_results
    assert db.status == "completed" and result.data_result.product_id == "SSCRJU"  # type: ignore[union-attr]
    assert result.data_result.count == 2  # type: ignore[union-attr]
    assert rag.status in {"completed", "partial"}
    assert "swg21996508" in rag.payload.retrieved_doc_ids  # type: ignore[union-attr]
    assert all(c.quote for c in result.citations)
    assert result.usage.llm_calls == 0 and result.usage.db_queries == 1


def test_scoped_subject_gets_partial_not_leak(supervisor) -> None:  # type: ignore[no-untyped-def]
    result = asyncio.run(supervisor.run(AnalysisRequest(query=QUESTION),
                                        context(products={"SSFKSJ"})))
    assert result.worker_results[1].status == "permission_denied"
    assert result.data_result is None and result.status in {"partial", "permission_denied"}
