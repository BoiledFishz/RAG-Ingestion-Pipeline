"""Single ReAct agent and a supervisor that executes the validated plan DAG."""

from __future__ import annotations

import logging
import re
import time
from collections.abc import Awaitable, Callable

from agents.critic import INSUFFICIENT_DIAGNOSIS, CriticLoop
from agents.planner import LLMPlanner, validate_review_paths
from agents.research import ReActResearchAgent
from models.llm import MeteredModel
from models.schemas import (
    AgentName,
    CriticLoopRun,
    Document,
    Metrics,
    PlannedTask,
    RAGResponse,
    ResearchRun,
    SystemRun,
    TaskExecution,
)

LOGGER = logging.getLogger(__name__)
Handler = Callable[[str, PlannedTask, list[TaskExecution]], Awaitable[TaskExecution]]
REVIEW_FAILED = "复核未通过，无法生成可靠回答。"


def combine_responses(inputs: list[TaskExecution]) -> RAGResponse:
    """Preserve specialist answer bodies while remapping their local citations."""
    if any(result.status == "failed" for result in inputs):
        return RAGResponse(answer=REVIEW_FAILED, sources=[], confidence=0)
    sources = []
    answers = []
    confidence = []
    for result in inputs:
        response = result.response
        if not response.sources:
            continue
        mapping = {}
        for index, source in enumerate(response.sources, 1):
            if source not in sources:
                sources.append(source)
            mapping[str(index)] = str(sources.index(source) + 1)
        def remap_citation(match: re.Match[str], ids: dict[str, str] = mapping) -> str:
            return f"[{ids.get(match[1], match[1])}]"

        answer = re.sub(r"\[S?(\d+)\]", remap_citation, response.answer)
        if answer not in answers:
            answers.append(answer)
        confidence.append(response.confidence)
    return RAGResponse(
        answer="\n".join(answers) if answers else "没有找到足够证据。",
        sources=sources, confidence=min(confidence) if confidence else 0,
    )


def evidence_documents(inputs: list[TaskExecution]) -> list[Document]:
    """Pass only actual dependency evidence across the agent boundary."""
    unique: dict[tuple[str, str], Document] = {}
    for result in inputs:
        for source in result.response.sources:
            unique[(source.document_id, source.quote)] = Document(
                document_id=source.document_id, source=source.source,
                title=source.title or source.document_id, text=source.quote, score=1,
            )
    return list(unique.values())


class SingleAgentVersion:
    def __init__(self, research: ReActResearchAgent) -> None:
        self.research = research

    async def run(self, query: str) -> SystemRun:
        research = await self.research.run(query)
        return SystemRun(response=research.response, metrics=research.metrics, research=research)


class MultiAgentVersion:
    """Dispatch registered specialists in DAG order and retain each task's result."""

    def __init__(
        self, planner: LLMPlanner, research: ReActResearchAgent, critic: CriticLoop,
        model_meter: MeteredModel | None = None,
    ) -> None:
        self.planner, self.research, self.critic = planner, research, critic
        self.model_meter = model_meter

    async def run(self, query: str) -> SystemRun:
        started = time.perf_counter()
        before = self.model_meter.snapshot() if self.model_meter else Metrics()
        research_runs: list[ResearchRun] = []
        critic_runs: list[CriticLoopRun] = []

        def outcome(
            task: PlannedTask, response: RAGResponse, *, status: str = "", detail: str = "",
        ) -> TaskExecution:
            return TaskExecution.model_validate({
                **task.model_dump(), "response": response,
                "status": status or ("completed" if response.sources else "refused"),
                "detail": detail,
            })

        async def research_task(
            question: str, task: PlannedTask, inputs: list[TaskExecution],
        ) -> TaskExecution:
            run = await self.research.run(
                question, objective=task.objective, prior_evidence=evidence_documents(inputs),
            )
            research_runs.append(run)
            return outcome(task, run.response)

        async def analysis_task(
            question: str, task: PlannedTask, inputs: list[TaskExecution],
        ) -> TaskExecution:
            # Select supporting facts instead of inventing unavailable logs or telemetry.
            response = combine_responses(inputs)
            return outcome(task, response,
                           status="failed" if any(r.status == "failed" for r in inputs) else "",
                           detail=f"Evidence analysis: {task.objective}")

        async def diagnosis_task(
            question: str, task: PlannedTask, inputs: list[TaskExecution],
        ) -> TaskExecution:
            supported = combine_responses(inputs)
            if not supported.sources:
                return outcome(task, supported, detail="Dependencies supplied no relevant evidence")
            evidence = "\n".join(
                f"[{index}] {source.quote}" for index, source in enumerate(supported.sources, 1)
            )
            checked = await self.critic.run(
                f"User question: {question}\nAssigned objective: {task.objective}", evidence,
                source_context={str(i): {"title": source.title,
                                         "applicability": source.applicability}
                                for i, source in enumerate(supported.sources, 1)},
            )
            critic_runs.append(checked)
            if not checked.passed:
                return outcome(task, RAGResponse(
                    answer=REVIEW_FAILED, sources=[], confidence=0,
                ), status="failed", detail=checked.final_diagnosis)
            if checked.final_diagnosis.startswith(INSUFFICIENT_DIAGNOSIS):
                return outcome(task, RAGResponse(
                    answer="知识库中没有足够信息回答该问题。", sources=[], confidence=0,
                ), status="refused", detail=checked.final_diagnosis)
            draft = checked.final_diagnosis.replace("[evidence]", "[1]")
            citations = re.findall(r"\[S?(\d+)\]", draft)
            valid = checked.passed and bool(citations) and all(
                1 <= int(value) <= len(supported.sources) for value in citations
            )
            # Publish only after review and citation validation both pass.
            response = supported.model_copy(update={"answer": draft}) if valid else RAGResponse(
                answer=REVIEW_FAILED, sources=[], confidence=0,
            )
            return outcome(
                task, response, status="completed" if valid else "failed",
                detail=checked.final_diagnosis,
            )

        async def report_task(
            question: str, task: PlannedTask, inputs: list[TaskExecution],
        ) -> TaskExecution:
            response = combine_responses(inputs)
            return outcome(task, response,
                           status="failed" if any(r.status == "failed" for r in inputs) else "",
                           detail=f"Evidence-backed report: {task.objective}")

        registry: dict[AgentName, Handler] = {
            AgentName.research_agent: research_task,
            AgentName.data_analyst: analysis_task,
            AgentName.diagnosis_agent: diagnosis_task,
            AgentName.report_writer: report_task,
        }
        plan = await self.planner.run(query)
        validate_review_paths(plan)
        executed: dict[str, TaskExecution] = {}
        for task in plan.tasks:
            dependencies = [executed[identifier] for identifier in task.dependencies]
            LOGGER.info("Executing %s agent=%s dependencies=%s", task.task_id,
                        task.agent, task.dependencies)
            executed[task.task_id] = await registry[task.agent](query, task, dependencies)

        # Only terminal outputs may contribute to the final response. This also prevents
        # undeclared cross-task access through a global evidence cache.
        consumed = {identifier for task in plan.tasks for identifier in task.dependencies}
        terminal = [result for key, result in executed.items() if key not in consumed]
        response = combine_responses(terminal)
        measured = self.model_meter.delta(before) if self.model_meter else Metrics()
        measured.tool_calls = sum(run.metrics.tool_calls for run in research_runs)
        measured.latency_ms = (time.perf_counter() - started) * 1000
        return SystemRun(
            response=response, metrics=measured, plan=plan,
            research=research_runs[-1] if research_runs else None,
            critic=critic_runs[-1] if critic_runs else None,
            executions=list(executed.values()),
        )
