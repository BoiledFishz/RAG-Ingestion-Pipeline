from __future__ import annotations

from pathlib import Path
from uuid import uuid4

import pytest

from agents.chap12.contracts import TrustedContext
from agents.chap12.sample import write_index

AGENT_ROOT = Path(__file__).resolve().parents[2]
ALL_OPS = {"count_documents", "count_by_year", "list_recent_documents"}


def fixture_docs() -> list[dict[str, object]]:
    """Committed official TechQA documents (no synthetic text)."""
    from rag.techqa.data import documents

    return list(documents("fixture"))


@pytest.fixture(scope="session")
def sample_index() -> Path:
    path = AGENT_ROOT / ".test_tmp" / f"chap12-{uuid4().hex}" / "sample.sqlite"
    write_index(path, fixture_docs(), {"seed": "test", "questions": "fixture"})
    return path


def context(workers: set[str] | None = None, ops: set[str] | None = None,
            products: set[str] | None = None) -> TrustedContext:
    return TrustedContext.model_validate({
        "subject_id": "tester", "tenant_id": "course",
        "allowed_workers": {"rag", "database"} if workers is None else workers,
        "allowed_db_operations": ALL_OPS if ops is None else ops,
        "allowed_product_ids": {"*"} if products is None else products,
    })
