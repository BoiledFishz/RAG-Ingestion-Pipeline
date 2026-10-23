"""Items 7 and 8: product-scoped related documents and validated model product pick."""

from __future__ import annotations

import asyncio
import json
from datetime import date
from pathlib import Path
from typing import Any

import pytest

from agents.chap12 import planner
from agents.chap12.budget import Budget, BudgetedModel, BudgetLimits
from agents.chap12.contracts import AnalysisRequest, DataRequest, DbInput
from agents.chap12.db_worker import DatabaseQueryWorker
from agents.chap12.product_pick import ProductPicker, pick_mode
from models.errors import DependencyUnavailable
from tests.chap12.conftest import context, fixture_docs

STREAMS = ("STREAMS 4.1.1.1 jobs do not inherit the environment variables set in .bashrc "
           "after upgrade")
WAS = "WebSphere MQ reason 2035 MQRC_NOT_AUTHORIZED when connecting"


def run(worker: DatabaseQueryWorker, request: DbInput, ctx=None):  # type: ignore[no-untyped-def]
    budget = Budget(BudgetLimits())
    return asyncio.run(worker.run("r", "t", request, ctx or context(), budget)), budget


def docs_of(product: str) -> set[str]:
    out = set()
    for doc in fixture_docs():
        meta = doc["metadata"]
        assert isinstance(meta, dict)
        if product in {p.strip() for p in str(meta.get("productId") or "").split(",")}:
            out.add(str(doc.get("id") or doc.get("doc_id")))
    return out


class FakeModel:
    def __init__(self, reply: Any) -> None:
        self.reply, self.prompts = reply, []  # type: ignore[var-annotated]

    async def generate(self, prompt: str, schema: dict[str, Any]) -> str:
        self.prompts.append(prompt)
        if isinstance(self.reply, Exception):
            raise self.reply
        return self.reply if isinstance(self.reply, str) else json.dumps(self.reply)


# ---- item 7: search_product_documents -------------------------------------------------

def test_related_documents_are_the_products_most_relevant(sample_index: Path) -> None:
    worker = DatabaseQueryWorker(sample_index)
    result, budget = run(worker, DbInput(operation="search_product_documents",
                                         product="SSCRJU", query=STREAMS))
    keys = [r.key for r in result.payload.rows]  # type: ignore[union-attr]
    assert result.status == "completed" and keys[0] == "swg21996508"
    assert set(keys) <= docs_of("SSCRJU")
    assert budget.used["db"] == 1


def test_related_documents_never_leave_the_product_or_filters(sample_index: Path) -> None:
    worker = DatabaseQueryWorker(sample_index)
    # A question about another product still returns only SSFKSJ documents.
    result, _ = run(worker, DbInput(operation="search_product_documents", product="SSFKSJ",
                                    query=STREAMS + " " + WAS, doc_class="apar"))
    keys = {r.key for r in result.payload.rows}  # type: ignore[union-attr]
    assert keys and keys <= docs_of("SSFKSJ") and all(k.startswith("swg1") for k in keys)
    dated, _ = run(worker, DbInput(operation="search_product_documents", product="SSFKSJ",
                                   query=WAS, date_from=date(2030, 1, 1)))
    assert dated.status == "no_data" and dated.payload.rows == []  # type: ignore[union-attr]


@pytest.mark.parametrize("query", ["x' OR 1=1 --", "\") UNION SELECT * FROM docs --"])
def test_related_documents_query_text_is_never_sql(sample_index: Path, query: str) -> None:
    worker = DatabaseQueryWorker(sample_index)
    result, _ = run(worker, DbInput(operation="search_product_documents", product="SSFKSJ",
                                    query=query))
    assert result.status in {"completed", "no_data"}
    assert {r.key for r in result.payload.rows} <= docs_of("SSFKSJ")  # type: ignore[union-attr]


def test_related_documents_require_the_question(sample_index: Path) -> None:
    worker = DatabaseQueryWorker(sample_index)
    result, _ = run(worker, DbInput(operation="search_product_documents", product="SSFKSJ"))
    assert result.status == "failed" and result.error.category == "invalid_input"  # type: ignore[union-attr]


def test_planner_defaults_and_explicit_request_carries_query(sample_index: Path) -> None:
    catalog = DatabaseQueryWorker(sample_index).catalog
    combined, _ = planner.db_input(AnalysisRequest(query=STREAMS), catalog)
    assert combined.operation == "search_product_documents" and combined.query == STREAMS
    data, _ = planner.db_input(AnalysisRequest(query=STREAMS, goal="data"), catalog)
    assert data.operation == "count_documents"
    explicit, _ = planner.db_input(AnalysisRequest(
        query=WAS, data_request=DataRequest(operation="search_product_documents",
                                            product="SSFKSJ")), catalog)
    assert explicit.query == WAS and explicit.product_source == "explicit"


# ---- item 8: model pick with program validation ----------------------------------------

def picking_worker(sample_index: Path, reply: Any, mode: str = "first",
                   ) -> tuple[DatabaseQueryWorker, FakeModel]:
    model = FakeModel(reply)
    worker = DatabaseQueryWorker(sample_index, picker=ProductPicker(BudgetedModel(model)),
                                 pick_mode=mode)
    return worker, model


def unnamed(query: str = STREAMS) -> DbInput:
    return DbInput(operation="count_documents", infer_product=True, query=query,
                   product_source="query_literal")


def test_valid_pick_is_used_labelled_and_metered(sample_index: Path) -> None:
    worker, model = picking_worker(sample_index, {"choice": 1})
    result, budget = run(worker, unnamed())
    assert result.status == "completed"
    assert result.payload.product_source == "model_pick"  # type: ignore[union-attr]
    assert result.payload.product_id == "SSCRJU"  # top candidate of the Streams question  # type: ignore[union-attr]
    assert "模型从程序给出的候选产品列表" in result.limitations[0]
    assert budget.used["llm"] == 1 and len(model.prompts) == 1
    assert "KIND: PRODUCT_PICK" in model.prompts[0] and "(SSCRJU)" in model.prompts[0]


@pytest.mark.parametrize("reply", [{"choice": 0}, {"choice": 99}, {"choice": -1},
                                   {"choice": "1"}, {"choice": True}, "not json", {},
                                   DependencyUnavailable("down")])
def test_invalid_or_declined_pick_falls_back_to_rule(sample_index: Path, reply: Any) -> None:
    worker, _ = picking_worker(sample_index, reply)
    result, _ = run(worker, unnamed())
    # Fallback: the deterministic BM25 inference (Streams question -> SSCRJU, inferred).
    assert result.payload.product_source == "inferred"  # type: ignore[union-attr]


def test_invalid_pick_without_rule_asks_for_clarification(
        sample_index: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    worker, _ = picking_worker(sample_index, {"choice": 42})
    monkeypatch.setattr(worker, "_infer", lambda query, ctx: (None, []))
    result, _ = run(worker, unnamed())
    assert result.status == "no_data" and result.error.category == "clarification_required"  # type: ignore[union-attr]


def test_fallback_mode_calls_model_only_when_rule_fails(
        sample_index: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    worker, model = picking_worker(sample_index, {"choice": 1}, mode="fallback")
    result, budget = run(worker, unnamed())
    assert result.payload.product_source == "inferred" and model.prompts == []  # type: ignore[union-attr]
    assert budget.used["llm"] == 0
    monkeypatch.setattr(worker, "_infer", lambda query, ctx: (None, []))
    picked, _ = run(worker, unnamed())
    assert picked.payload.product_source == "model_pick" and len(model.prompts) == 1  # type: ignore[union-attr]


def test_off_mode_never_calls_model(sample_index: Path) -> None:
    worker, model = picking_worker(sample_index, {"choice": 1}, mode="off")
    run(worker, unnamed())
    assert model.prompts == []


def test_unauthorized_products_are_never_offered(sample_index: Path) -> None:
    worker, model = picking_worker(sample_index, {"choice": 1})
    result, _ = run(worker, unnamed(WAS), context(products={"SSFKSJ"}))
    assert result.payload.product_id == "SSFKSJ"  # type: ignore[union-attr]
    offered = model.prompts[0].split("CANDIDATES:")[1]
    assert "(SSFKSJ)" in offered
    assert all(f"({p})" not in offered for p in ("SSEQTP", "SS7K4U", "SSYHRD", "SSCRJU"))


def test_explicit_product_never_calls_model(sample_index: Path) -> None:
    worker, model = picking_worker(sample_index, {"choice": 1})
    result, _ = run(worker, DbInput(operation="count_documents", product="SSFKSJ"))
    assert result.status == "completed" and model.prompts == []


def test_pick_mode_env_override(monkeypatch: pytest.MonkeyPatch) -> None:
    for mode in ("off", "fallback", "first"):
        monkeypatch.setenv("CHAP12_PRODUCT_PICK", mode)
        assert pick_mode() == mode
