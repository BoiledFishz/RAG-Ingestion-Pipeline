from __future__ import annotations

from fastapi import FastAPI
from pydantic import BaseModel, Field

from agents.systems import MultiAgentVersion, SingleAgentVersion
from evaluation.factory import build_advanced, build_rag, model_from_env
from models.schemas import CriticLoopRun, RAGResponse, ResearchRun, StructuredPlan, SystemRun

app = FastAPI(title="Agentic RAG Homework", version="1.0.0")


class Query(BaseModel):
    query: str = Field(min_length=1, max_length=2000)


class CriticRequest(BaseModel):
    task: str = Field(min_length=1, max_length=2000)
    evidence: str = Field(min_length=1, max_length=10000)


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
    return await critic.run(request.task, request.evidence)


@app.post("/v1/single-agent", response_model=SystemRun)
async def single_agent(request: Query) -> SystemRun:
    _, _, research_agent, _ = build_advanced(model_from_env())
    return await SingleAgentVersion(research_agent).run(request.query)


@app.post("/v1/multi-agent", response_model=SystemRun)
async def multi_agent(request: Query) -> SystemRun:
    meter, planner, research_agent, critic = build_advanced(model_from_env())
    return await MultiAgentVersion(planner, research_agent, critic, meter).run(request.query)
