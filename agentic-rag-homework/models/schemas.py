from __future__ import annotations

from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)


class Document(StrictModel):
    document_id: str
    title: str
    text: str
    source: str
    score: float = 0
    retrieved_excerpt: str = ""


class Source(StrictModel):
    document_id: str
    source: str
    quote: str
    title: str = ""
    applicability: str = ""


class RAGResponse(StrictModel):
    answer: str
    sources: list[Source] = Field(default_factory=list)
    confidence: float = Field(ge=0, le=1)

    @model_validator(mode="after")
    def evidence_consistency(self) -> RAGResponse:
        if not self.sources and self.confidence != 0:
            raise ValueError("responses without sources must have zero confidence")
        return self


class RewriteDecision(StrictModel):
    rewritten_query: str
    action: Literal["retrieve", "clarify"]
    clarification: str = ""

    @model_validator(mode="after")
    def clarification_required(self) -> RewriteDecision:
        if self.action == "clarify" and not self.clarification.strip():
            raise ValueError("clarify requires a question")
        return self


class AgentName(StrEnum):
    research_agent = "research_agent"
    data_analyst = "data_analyst"
    diagnosis_agent = "diagnosis_agent"
    report_writer = "report_writer"


class PlannedTask(StrictModel):
    task_id: str = Field(pattern=r"^T\d{3}$")
    agent: AgentName
    objective: str = Field(min_length=8, max_length=500)
    dependencies: list[str] = Field(default_factory=list)


class StructuredPlan(StrictModel):
    tasks: list[PlannedTask] = Field(min_length=1, max_length=8)

    @model_validator(mode="after")
    def validate_dag(self) -> StructuredPlan:
        ids = [task.task_id for task in self.tasks]
        if len(ids) != len(set(ids)):
            raise ValueError("task IDs must be unique")
        prior: set[str] = set()
        for expected, task in enumerate(self.tasks, 1):
            if task.task_id != f"T{expected:03d}":
                raise ValueError("task IDs must be sequential from T001")
            if len(task.dependencies) != len(set(task.dependencies)):
                raise ValueError("dependencies must be unique")
            if not set(task.dependencies) <= prior:
                raise ValueError("dependencies must reference earlier tasks")
            prior.add(task.task_id)
        return self


class ResearchAction(StrictModel):
    action: Literal["rag_search", "search", "read_document", "finish"]
    argument: str = ""
    reason: str = Field(min_length=3)

    @model_validator(mode="after")
    def action_argument(self) -> ResearchAction:
        if self.action != "finish" and not self.argument.strip():
            raise ValueError("tool actions require an argument")
        return self


class ResearchStep(StrictModel):
    index: int
    action: str
    argument: str
    reason: str
    observation_ids: list[str] = Field(default_factory=list)
    observation: str = ""


class Metrics(StrictModel):
    llm_calls: int = 0
    model_errors: int = 0
    tool_calls: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    latency_ms: float = 0

    @property
    def token_usage(self) -> int:
        return self.input_tokens + self.output_tokens


class ResearchRun(StrictModel):
    response: RAGResponse
    steps: list[ResearchStep]
    stop_reason: Literal["finished", "max_steps", "no_evidence"]
    metrics: Metrics


class CriticIssue(StrictModel):
    code: str
    description: str = Field(max_length=400)
    suggestion: str = Field(max_length=400)


class CriticResult(StrictModel):
    passed: bool
    score: float = Field(ge=0, le=1)
    issues: list[CriticIssue] = Field(default_factory=list, max_length=3)

    @model_validator(mode="after")
    def issue_consistency(self) -> CriticResult:
        if self.passed != (len(self.issues) == 0):
            raise ValueError("passed must be true exactly when issue list is empty")
        return self


class DiagnosisDraft(StrictModel):
    diagnosis: str = Field(min_length=10, max_length=2200)
    citations: list[str] = Field(min_length=1, max_length=4,
                               description="Unique supporting evidence IDs, without brackets")


class CriticAttempt(StrictModel):
    attempt: int
    diagnosis: str
    critique: CriticResult
    resolved_previous_issues: list[str] = Field(default_factory=list)


class CriticLoopRun(StrictModel):
    final_diagnosis: str
    passed: bool
    answer_sufficient: bool = True
    retries: int = Field(ge=0, le=2)
    attempts: list[CriticAttempt]
    metrics: Metrics


class ComparisonRow(StrictModel):
    version: Literal["A_single", "B_multi"]
    llm_calls: float
    token_usage: float
    latency_ms: float
    answer_quality: float
    failure_rate: float


class TaskExecution(StrictModel):
    task_id: str
    agent: AgentName
    objective: str
    dependencies: list[str]
    response: RAGResponse
    status: Literal["completed", "refused", "fallback", "failed"] = "completed"
    detail: str = ""


class SystemRun(StrictModel):
    response: RAGResponse
    metrics: Metrics
    plan: StructuredPlan | None = None
    research: ResearchRun | None = None
    critic: CriticLoopRun | None = None
    executions: list[TaskExecution] = Field(default_factory=list)
