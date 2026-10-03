from __future__ import annotations

import logging

import httpx
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field, model_validator

from agents.critic import evidence_blocks
from agents.systems import MultiAgentVersion, SingleAgentVersion
from evaluation.factory import build_advanced, build_rag, model_from_env
from models.errors import ModelUnavailable
from models.schemas import CriticLoopRun, RAGResponse, ResearchRun, StructuredPlan, SystemRun

app = FastAPI(title="Agentic RAG Homework", version="1.0.0")


@app.exception_handler(httpx.HTTPError)
@app.exception_handler(ModelUnavailable)
async def dependency_error(
    request: Request, exc: httpx.HTTPError | ModelUnavailable,
) -> JSONResponse:
    logging.getLogger(__name__).warning("Model dependency failed: %s", type(exc).__name__)
    return JSONResponse(status_code=503, content={"detail": "Model dependency unavailable"})


class Query(BaseModel):
    query: str = Field(min_length=1, max_length=2000)


class SourceContext(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    title: str = Field(default="", max_length=200)
    applicability: str = Field(default="", max_length=500)


class CriticRequest(BaseModel):
    task: str = Field(min_length=1, max_length=2000)
    evidence: str = Field(min_length=1, max_length=10000)
    source_context: dict[str, SourceContext] = Field(default_factory=dict, max_length=8)

    @model_validator(mode="after")
    def context_matches_evidence(self) -> CriticRequest:
        if not set(self.source_context) <= set(evidence_blocks(self.evidence)):
            raise ValueError("Source context must reference supplied evidence IDs")
        return self


@app.get("/healthz")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/v1/rag/query", response_model=RAGResponse)
async def rag_query(request: Query) -> RAGResponse:
    return await build_rag().run(request.query)


@app.post("/v1/planner", response_model=StructuredPlan)
async def create_plan(request: Query) -> StructuredPlan:
    _, planner, _, _ = build_advanced(model_from_env())
    return await planner.run(request.query)


@app.post("/v1/research", response_model=ResearchRun)
async def research(request: Query) -> ResearchRun:
    _, _, agent, _ = build_advanced(model_from_env())
    return await agent.run(request.query)


@app.post("/v1/critic-loop", response_model=CriticLoopRun)
async def critic_loop(request: CriticRequest) -> CriticLoopRun:
    _, _, _, critic = build_advanced(model_from_env())
    run = await critic.run(request.task, request.evidence, {
        key: value.model_dump() for key, value in request.source_context.items()
    })
    require_critic_dependency(run)
    return run


def require_critic_dependency(run: CriticLoopRun | None) -> None:
    if run and any(issue.code == "model_unavailable" for attempt in run.attempts
                   for issue in attempt.critique.issues):
        raise ModelUnavailable("Critic model dependency unavailable")


@app.post("/v1/single-agent", response_model=SystemRun)
async def single_agent(request: Query) -> SystemRun:
    _, _, research_agent, _ = build_advanced(model_from_env())
    return await SingleAgentVersion(research_agent).run(request.query)


@app.post("/v1/multi-agent", response_model=SystemRun)
async def multi_agent(request: Query) -> SystemRun:
    meter, planner, research_agent, critic = build_advanced(model_from_env())
    run = await MultiAgentVersion(planner, research_agent, critic, meter).run(request.query)
    require_critic_dependency(run.critic)
    return run
