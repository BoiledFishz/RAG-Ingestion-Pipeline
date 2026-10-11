"""Explicit, versioned contracts exchanged between Supervisor and Workers.

Workers never receive chat history: each gets only the fields of its own input model.
"""

from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

CONTRACT_VERSION = "chap12-v1"

WorkerStatus = Literal["completed", "partial", "no_data", "permission_denied", "timeout", "failed"]
WorkerName = Literal["rag", "database"]
Goal = Literal["explain", "data", "explain_and_data"]
DbOperation = Literal["count_documents", "count_by_year", "list_recent_documents"]
DocClass = Literal["apar", "technote", "product_documentation", "other"]

# Statuses that still carry publishable information for the user.
USEFUL: frozenset[str] = frozenset({"completed", "partial"})


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)


class DataRequest(Strict):
    """Optional explicit data question. Product is a catalogue name, never SQL."""

    operation: DbOperation = "count_documents"
    product: str | None = Field(default=None, min_length=1, max_length=120)
    date_from: date | None = None
    date_to: date | None = None
    doc_class: DocClass | None = None
    limit: int = Field(default=5, ge=1, le=10)

    @model_validator(mode="after")
    def ordered_range(self) -> DataRequest:
        if self.date_from and self.date_to and self.date_from > self.date_to:
            raise ValueError("date_from must not be after date_to")
        return self


class AnalysisRequest(Strict):
    query: str = Field(min_length=1, max_length=4000)
    goal: Goal = "explain_and_data"
    data_request: DataRequest | None = None

    @field_validator("query")
    @classmethod
    def nonblank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("query cannot be blank")
        return value


class TrustedContext(Strict):
    """Built only by the server from a verified credential; never from the request body."""

    subject_id: str
    tenant_id: str
    allowed_workers: frozenset[WorkerName]
    allowed_db_operations: frozenset[DbOperation]
    # "*" means every product of the sample snapshot; otherwise official productId values.
    allowed_product_ids: frozenset[str]

    def product_allowed(self, product_id: str) -> bool:
        return "*" in self.allowed_product_ids or product_id in self.allowed_product_ids


class TaskSpec(Strict):
    task_id: str
    worker: WorkerName
    required: bool = True


class Citation(Strict):
    source_id: str
    doc_id: str
    title: str = ""
    quote: str


class RagInput(Strict):
    query: str


class RagPayload(Strict):
    answer: str
    citations: list[Citation] = Field(default_factory=list)
    confidence: float = Field(ge=0, le=1)
    rag_status: str
    rewritten_query: str = ""
    retrieved_doc_ids: list[str] = Field(default_factory=list)


ProductSource = Literal["explicit", "query_literal", "inferred"]


class DbInput(Strict):
    operation: DbOperation
    product: str | None = None
    product_source: ProductSource = "explicit"
    # When no product is named, let the DB Worker infer one from its own BM25 index.
    infer_product: bool = False
    query: str | None = Field(default=None, max_length=4000)
    date_from: date | None = None
    date_to: date | None = None
    doc_class: DocClass | None = None
    limit: int = Field(default=5, ge=1, le=10)


class DbRow(Strict):
    key: str
    value: int | str


class DbPayload(Strict):
    operation: DbOperation
    product_name: str | None
    product_id: str | None
    product_source: ProductSource = "explicit"
    inference_doc_ids: list[str] = Field(default_factory=list)
    date_from: str | None
    date_to: str | None
    doc_class: str | None
    metric: str
    unit: str
    count: int | None = None
    rows: list[DbRow] = Field(default_factory=list)
    truncated: bool = False
    snapshot: str
    query_template: str


class WorkerError(Strict):
    category: Literal[
        "invalid_input", "clarification_required", "permission_denied", "timeout",
        "budget_exhausted", "dependency_unavailable", "invalid_evidence", "internal",
    ]
    message: str
    retryable: bool = False


class Usage(Strict):
    llm_calls: int = 0
    embedding_calls: int = 0
    db_queries: int = 0
    tool_calls: int = 0
    retries: int = 0
    # Local Ollama does not expose token counts through the reused adapter: unknown is null.
    tokens: int | None = None
    elapsed_ms: float = 0


class WorkerResult(Strict):
    contract_version: str = CONTRACT_VERSION
    run_id: str
    task_id: str
    worker: WorkerName
    status: WorkerStatus
    payload: RagPayload | DbPayload | None = None
    limitations: list[str] = Field(default_factory=list)
    error: WorkerError | None = None
    usage: Usage = Field(default_factory=Usage)

    @model_validator(mode="after")
    def payload_matches_status(self) -> WorkerResult:
        if self.status in USEFUL and self.payload is None:
            raise ValueError(f"{self.status} requires a payload")
        if self.status in {"permission_denied", "timeout", "failed"} and self.error is None:
            raise ValueError(f"{self.status} requires an error")
        return self


class TraceEvent(Strict):
    at_ms: float
    node: str
    event: str
    detail: str = ""


class FinalResponse(Strict):
    contract_version: str = CONTRACT_VERSION
    run_id: str
    status: WorkerStatus
    goal: Goal
    plan: list[TaskSpec]
    answer: str
    citations: list[Citation] = Field(default_factory=list)
    data_result: DbPayload | None = None
    limitations: list[str] = Field(default_factory=list)
    worker_results: list[WorkerResult]
    usage: Usage
    trace: list[TraceEvent] = Field(default_factory=list)
