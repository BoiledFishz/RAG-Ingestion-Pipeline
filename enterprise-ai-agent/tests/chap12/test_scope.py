"""P0-2: unauthorized products never reach RAG evidence, DB data or the response text."""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from agents.chap12.contracts import AnalysisRequest, DbInput
from agents.chap12.factory import build_supervisor
from agents.chap12.scope import DocumentScope, product_scope
from models.schemas import RetrieverInput
from models.settings import Settings
from tests.chap12.conftest import context
from tools.sample_retriever import SampleRetrieverTool

STREAMS_DOCS = {"swg21996508", "swg27038498"}  # official fixture docs tagged SSCRJU
STREAMS_MARKERS = ["SSCRJU", "swg21996508", "swg27038498", "STREAMS", "Streams"]
QUESTION = ("User environment variables no longer getting picked up after upgrade to Streams "
            "4.1.1.1 or 4.1.1.2? Environment variables set in .bashrc are no longer being set.")
UNNAMED = "Jobs do not pick up environment variables from .bashrc with ODBC operators"


@pytest.fixture
def supervisor(sample_index: Path, monkeypatch: pytest.MonkeyPatch):  # type: ignore[no-untyped-def]
    monkeypatch.setenv("TECHQA_PROFILE", "fixture")
    return build_supervisor(Settings(profile="offline"), sample_index)


def test_retrieval_is_filtered_before_ranking(sample_index: Path) -> None:
    tool = SampleRetrieverTool(sample_index, rerank="lexical", use_dense=False)
    scope = DocumentScope(sample_index)
    unrestricted = asyncio.run(tool.invoke(RetrieverInput(query=QUESTION, top_k=8)))
    assert STREAMS_DOCS & {d.chunk_id.split(":")[1] for d in unrestricted}

    async def scoped() -> list[str]:
        with product_scope(frozenset({"SSFKSJ"})):
            docs = await tool.invoke(RetrieverInput(query=QUESTION, top_k=8))
        return [d.chunk_id.split(":")[1] for d in docs]

    kept = asyncio.run(scoped())
    assert kept and not STREAMS_DOCS & set(kept)
    assert all("SSFKSJ" in scope.products[d] for d in kept)


def test_denied_product_absent_from_citations_data_and_text(supervisor) -> None:  # type: ignore[no-untyped-def]
    result = asyncio.run(supervisor.run(AnalysisRequest(query=QUESTION),
                                        context(products={"SSFKSJ"})))
    rag, db = result.worker_results
    assert db.status == "permission_denied" and result.data_result is None
    assert not STREAMS_DOCS & {c.doc_id for c in result.citations}
    assert not STREAMS_DOCS & set(rag.payload.retrieved_doc_ids if rag.payload else [])  # type: ignore[union-attr]
    dumped = result.model_dump_json()
    assert not [m for m in ("SSCRJU", "swg21996508", "swg27038498") if m in dumped]


def test_inference_never_reveals_unauthorized_product(supervisor) -> None:  # type: ignore[no-untyped-def]
    # Unrestricted, the question is inferred as IBM Streams (see test_db_worker).
    full = asyncio.run(supervisor.run(AnalysisRequest(query=UNNAMED, goal="data"), context()))
    assert full.data_result is not None and full.data_result.product_id == "SSCRJU"
    scoped = asyncio.run(supervisor.run(AnalysisRequest(query=UNNAMED, goal="data"),
                                        context(products={"SSFKSJ"})))
    dumped = scoped.model_dump_json()
    assert not [m for m in STREAMS_MARKERS if m in dumped]
    assert scoped.worker_results[0].status in {"no_data", "completed"}
    if scoped.data_result is not None:
        assert scoped.data_result.product_id == "SSFKSJ"


def test_inference_scope_unit(sample_index: Path) -> None:
    from agents.chap12.db_worker import DatabaseQueryWorker

    worker = DatabaseQueryWorker(sample_index)
    product, docs = worker._infer(UNNAMED, context(products={"SSFKSJ"}))
    assert product in {None, "SSFKSJ"} and not STREAMS_DOCS & set(docs)
    assert DbInput(operation="count_documents").product is None
