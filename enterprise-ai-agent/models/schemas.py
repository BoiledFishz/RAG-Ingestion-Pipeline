"""Strict JSON contracts shared by the tool, agent, API and evaluation."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

MetadataValue = str | int | float | bool


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)


class QueryRequest(StrictModel):
    query: str = Field(min_length=1, max_length=2000)
    filters: dict[str, MetadataValue] = Field(default_factory=dict)

    @model_validator(mode="after")
    def nonblank(self) -> QueryRequest:
        self.query = self.query.strip()
        if not self.query:
            raise ValueError("query cannot be blank")
        return self


class RetrieverInput(StrictModel):
    query: str = Field(min_length=1, max_length=2000)
    top_k: int = Field(default=8, ge=1, le=30)
    filters: dict[str, MetadataValue] = Field(default_factory=dict)


class Document(StrictModel):
    chunk_id: str = Field(min_length=1)
    text: str = Field(min_length=1)
    source_file: str
    page_number: int | str = 1
    score: float = 0.0
    metadata: dict[str, MetadataValue] = Field(default_factory=dict)


class RewriteDraft(StrictModel):
    """Wire schema uses required fields only; runtime flags are never model-controlled."""

    query: str
    action: Literal["retrieve", "clarify"]
    clarification: str


class RewriteDecision(StrictModel):
    query: str = Field(min_length=1, max_length=2000)
    action: Literal["retrieve", "clarify"] = "retrieve"
    clarification: str = ""
    fallback: bool = False

    @model_validator(mode="after")
    def clarification_required(self) -> RewriteDecision:
        if self.action == "clarify" and not self.clarification.strip():
            raise ValueError("clarification is required for action=clarify")
        return self


class Evidence(StrictModel):
    source_id: str
    chunk_id: str
    source_file: str
    page_number: int | str
    excerpt: str
    relevance: float = Field(ge=0, le=1)
    tokens: int = Field(ge=0)


class CompressionResult(StrictModel):
    evidence: list[Evidence] = Field(default_factory=list)
    original_tokens: int = 0
    context_tokens: int = 0


class Quotation(StrictModel):
    source_id: str = Field(pattern=r"^S[1-9][0-9]*$")
    quote: str = Field(min_length=8, max_length=6000)


class SelectionDraft(StrictModel):
    # Only exact quotations can enter the final answer. No free-form factual claim.
    quotes: list[Quotation] = Field(default_factory=list, max_length=4)


class Source(StrictModel):
    source_id: str
    chunk_id: str
    source_file: str
    page_number: int | str
    quote: str


class AgentResponse(StrictModel):
    answer: str = Field(min_length=1)
    sources: list[Source] = Field(default_factory=list)
    confidence: float = Field(ge=0, le=1)

    @model_validator(mode="after")
    def consistent_evidence(self) -> AgentResponse:
        if not self.sources and self.confidence != 0:
            raise ValueError("a response without evidence must have confidence=0")
        return self


class RunTrace(StrictModel):
    original_query: str
    rewritten_query: str = ""
    rewrite_fallback: bool = False
    tool_called: bool = False
    candidate_ids: list[str] = Field(default_factory=list)
    evidence: list[Evidence] = Field(default_factory=list)
    original_tokens: int = 0
    context_tokens: int = 0
    status: Literal["answered", "clarified", "unanswerable", "invalid_evidence"] = "unanswerable"
    retries: int = 0
    latency_ms: float = 0


class AgentRun(StrictModel):
    response: AgentResponse
    trace: RunTrace
