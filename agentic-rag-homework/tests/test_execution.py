import asyncio

from agents.planner import LLMPlanner
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
    planner = LLMPlanner(ScriptedModel([{"tasks": tasks}]))
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
            task(3, "report_writer", ["T002"]),
        ]
    )
    assert [row.agent for row in run.executions] == [
        "research_agent",
        "data_analyst",
        "report_writer",
    ]
    assert run.critic is None  # No implicit diagnosis outside the supplied plan.
    assert "setproperty" in run.response.answer
    assert run.executions[2].response == run.executions[1].response


def test_independent_task_cannot_read_another_tasks_evidence():
    run = execute(
        [
            task(1, "research_agent", []),
            task(2, "report_writer", []),
            task(3, "report_writer", ["T002"]),
        ]
    )
    assert run.executions[0].response.sources
    assert not run.executions[1].response.sources
    assert not run.executions[2].response.sources


def test_report_only_plan_does_not_run_hidden_research():
    run = execute([task(1, "report_writer", [])])
    assert run.research is None
    assert run.critic is None
    assert run.metrics.tool_calls == 0
    assert not run.response.sources
