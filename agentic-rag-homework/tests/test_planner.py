import asyncio

import pytest

from agents.planner import LLMPlanner, PlannerValidationError
from models.llm import ScriptedModel


def test_planner_rejects_unknown_agent_then_repairs() -> None:
    model = ScriptedModel(
        [
            {
                "tasks": [
                    {
                        "task_id": "T001",
                        "agent": "invented_agent",
                        "objective": "Do a sufficiently specific task",
                        "dependencies": [],
                    }
                ]
            },
            {
                "tasks": [
                    {
                        "task_id": "T001",
                        "agent": "research_agent",
                        "objective": "Collect directly relevant supporting evidence",
                        "dependencies": [],
                    },
                    {
                        "task_id": "T002",
                        "agent": "report_writer",
                        "objective": "Write a sourced final investigation report",
                        "dependencies": ["T001"],
                    },
                ]
            },
        ]
    )
    plan = asyncio.run(LLMPlanner(model).run("Investigate an outage and report it"))
    assert [task.task_id for task in plan.tasks] == ["T001", "T002"]
    assert len(model.prompts) == 2
    assert "PREVIOUS_OUTPUT_INVALID" in model.prompts[1]


def test_planner_rejects_forward_dependency() -> None:
    model = ScriptedModel(
        [
            {
                "tasks": [
                    {
                        "task_id": "T001",
                        "agent": "research_agent",
                        "objective": "Collect directly relevant supporting evidence",
                        "dependencies": ["T002"],
                    },
                    {
                        "task_id": "T002",
                        "agent": "report_writer",
                        "objective": "Write the final evidence-backed report",
                        "dependencies": [],
                    },
                ]
            },
            {"tasks": []},
        ]
    )
    with pytest.raises(PlannerValidationError):
        asyncio.run(LLMPlanner(model).run("Investigate and report an outage"))
