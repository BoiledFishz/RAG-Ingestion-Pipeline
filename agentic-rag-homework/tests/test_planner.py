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
                        "agent": "diagnosis_agent",
                        "objective": "Review the evidence with the diagnosis Critic",
                        "dependencies": ["T001"],
                    },
                    {
                        "task_id": "T003",
                        "agent": "report_writer",
                        "objective": "Write a sourced final investigation report",
                        "dependencies": ["T002"],
                    },
                ]
            },
        ]
    )
    plan = asyncio.run(LLMPlanner(model).run("Investigate an outage and report it"))
    assert [task.task_id for task in plan.tasks] == ["T001", "T002", "T003"]
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


def test_planner_rejects_unreviewed_branch_even_when_another_branch_has_critic():
    from rag.techqa.data import question_text, questions

    from evaluation.demo_model import DemoStructuredModel

    unsafe = {"tasks": [
        {"task_id": "T001", "agent": "research_agent",
         "objective": "Collect official supporting evidence", "dependencies": []},
        {"task_id": "T002", "agent": "diagnosis_agent",
         "objective": "Review the first evidence with Critic", "dependencies": ["T001"]},
        {"task_id": "T003", "agent": "research_agent",
         "objective": "Collect additional unreviewed evidence", "dependencies": []},
        {"task_id": "T004", "agent": "report_writer",
         "objective": "Merge reviewed and unreviewed branches", "dependencies": ["T002", "T003"]},
    ]}
    safe = asyncio.run(DemoStructuredModel().generate("KIND: PLANNER", {}))
    model = ScriptedModel([unsafe, safe])
    plan = asyncio.run(LLMPlanner(model).run(question_text(questions("fixture")[0])))
    assert len(model.prompts) == 2
    assert "Every terminal answer branch" in model.prompts[1]
    assert plan.tasks[-1].dependencies == ["T002"]
