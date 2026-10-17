"""Deterministic planner: goal -> registered tasks; request -> typed Worker inputs.

No model chooses nodes, tools or permissions. Unknown goals are rejected by the request
schema; tasks whose worker is not registered are rejected by the Supervisor.
"""

from __future__ import annotations

from agents.chap12.contracts import AnalysisRequest, DbInput, RagInput, TaskSpec, WorkerName
from agents.chap12.db_worker import Catalog

GOAL_TASKS: dict[str, tuple[WorkerName, ...]] = {
    "explain": ("rag",),
    "data": ("database",),
    "explain_and_data": ("rag", "database"),
}


def plan(request: AnalysisRequest) -> list[TaskSpec]:
    return [TaskSpec(task_id=f"T{i}-{worker}", worker=worker)
            for i, worker in enumerate(GOAL_TASKS[request.goal], 1)]


def rag_input(request: AnalysisRequest) -> RagInput:
    return RagInput(query=request.query)


def db_input(request: AnalysisRequest, catalog: Catalog) -> tuple[DbInput, list[str]]:
    """Explicit data_request wins; otherwise the first catalogue product named in the query."""
    notes: list[str] = []
    explicit = request.data_request
    if explicit is not None and explicit.product is not None:
        return DbInput(**explicit.model_dump(), product_source="explicit",
                       query=request.query), notes
    found = catalog.find(request.query)
    product = found[0].product_id if found else None
    if len(found) > 1:
        notes.append("问题中识别到多个产品，数据查询只使用首个："
                     + "、".join(p.name for p in found[:4]))
    base = explicit.model_dump() if explicit is not None else {}
    # P1-5 / item 7: in a combined task the data part serves the answer: the product's
    # documents most relevant to the question (product-scoped BM25; chosen on the tune split
    # over "most recent", evaluation/chap12/tune/product_study.json) are returned as "related
    # documents". A pure data question defaults to a count (coverage metric, not business).
    default = "search_product_documents" if request.goal == "explain_and_data" else \
        "count_documents"
    return DbInput(**{**base, "operation": base.get("operation", default),
                      "product": product, "product_source": "query_literal",
                      "infer_product": product is None, "query": request.query}), notes
