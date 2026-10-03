import asyncio

import pytest

from agents.planner import LLMPlanner, PlannerValidationError
from agents.systems import MultiAgentVersion
from evaluation.factory import build_advanced
from models.llm import ScriptedModel


def task(number, agent, dependencies):
    return {
        "task_id": f"T{number:03d}",
        "agent": agent,
        "objective": "Answer the Streams environment question from supplied evidence",
        "dependencies": dependencies,
    }


def execute(tasks):
    meter, _, research, critic = build_advanced()
    planner = LLMPlanner(ScriptedModel([{"tasks": tasks}]), max_attempts=1)
    return asyncio.run(
        MultiAgentVersion(planner, research, critic, meter).run(
            "How are Streams environment variables set after upgrade to 4.1.1.2?"
        )
    )


def test_plan_drives_dispatch_and_dependencies():
    run = execute(
        [
            task(1, "research_agent", []),
            task(2, "data_analyst", ["T001"]),
            task(3, "diagnosis_agent", ["T002"]),
            task(4, "report_writer", ["T003"]),
        ]
    )
    assert [row.agent for row in run.executions] == [
        "research_agent",
        "data_analyst",
        "diagnosis_agent",
        "report_writer",
    ]
    assert run.critic is not None and run.critic.passed
    assert "setproperty" in run.response.answer
    assert run.executions[3].response == run.executions[2].response


def test_independent_task_cannot_read_another_tasks_evidence():
    meter, _, inner, critic = build_advanced()
    prior = []

    class RecordingResearch:
        async def run(self, question, objective, prior_evidence):
            prior.append([d.document_id for d in prior_evidence])
            return await inner.run(question, objective=objective, prior_evidence=prior_evidence)

    tasks = [
            task(1, "research_agent", []),
            task(2, "research_agent", []),
            task(3, "diagnosis_agent", ["T001"]),
            task(4, "diagnosis_agent", ["T002"]),
            task(5, "report_writer", ["T004"]),
    ]
    planner = LLMPlanner(ScriptedModel([{"tasks": tasks}]))
    run = asyncio.run(MultiAgentVersion(planner, RecordingResearch(), critic, meter).run(
        "How are Streams environment variables set after upgrade to 4.1.1.2?",
    ))
    assert prior == [[], []]
    assert run.executions[3].dependencies == ["T002"]
    assert run.executions[4].dependencies == ["T004"]


def test_report_only_plan_does_not_run_hidden_research():
    with pytest.raises(PlannerValidationError):
        execute([task(1, "report_writer", [])])
