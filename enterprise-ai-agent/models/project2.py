"""Strict Project 2 contracts, isolated from existing RAG API behavior."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

Status = Literal["completed", "partial", "no_data", "permission_denied", "timeout", "failed"]
Operation = Literal["document_count", "compare_document_counts", "list_matching_documents"]


class AnalysisRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    query: str = Field(min_length=1, max_length=20000)
    analysis_operation: Operation = "document_count"
    include_samples: bool = True
    sample_limit: int = Field(default=5, ge=0, le=10)
    analysis_predicates: list[list[str]] | None = None

    @field_validator("analysis_predicates")
    @classmethod
    def literal_groups(cls, value: list[list[str]] | None) -> list[list[str]] | None:
        if value is not None and (not 1 <= len(value) <= 2 or any(
            not 1 <= len(group) <= 3 or any(not phrase.strip() or len(phrase) > 120 for phrase in group)
            for group in value
        )):
            raise ValueError("At most two literal groups, three nonempty phrases per group, 120 chars each")
        return value


class WorkerResult(BaseModel):
    model_config = ConfigDict(extra="forbid")
    contract_version: str = "project2-v1"
    run_id: str
    task_id: str
    worker: Literal["rag", "database"]
    status: Status
    payload: dict[str, Any] = Field(default_factory=dict)
    evidence: list[dict[str, Any]] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    error: dict[str, Any] | None = None
    usage: dict[str, Any] = Field(default_factory=dict)
