"""Task 1: an LLM planner whose output is schema- and DAG-validated."""

from __future__ import annotations

import logging

from pydantic import ValidationError

from models.llm import StructuredModel
from models.schemas import AgentName, StructuredPlan

LOGGER = logging.getLogger(__name__)


class PlannerValidationError(RuntimeError):
    def __init__(self, attempts: list[dict[str, str]]) -> None:
        super().__init__(f"planner produced invalid output in {len(attempts)} attempts")
        self.attempts = attempts


class LLMPlanner:
    def __init__(self, model: StructuredModel, max_attempts: int = 2) -> None:
        self.model, self.max_attempts = model, max_attempts

    async def run(self, objective: str) -> StructuredPlan:
        if not objective.strip():
            raise ValueError("objective cannot be blank")
        allowed = ", ".join(item.value for item in AgentName)
        correction = ""
        attempts = []
        for _ in range(self.max_attempts):
            prompt = (
                "KIND: PLANNER\nDecompose the objective into the smallest useful DAG and return "
                "only schema-valid JSON. IDs must be sequential T001, T002... Dependencies may "
                "reference only earlier IDs. Never invent an agent. "
                "research_agent retrieves evidence; data_analyst selects supporting facts from "
                "dependencies; diagnosis_agent diagnoses and performs a critic loop using only "
                "dependency evidence; report_writer composes the evidence-backed final answer. "
                "Start with research_agent. All other agents need dependencies carrying evidence. "
                "Every plan must include diagnosis_agent. Every terminal output must be a "
                "diagnosis_agent or depend only on already reviewed outputs. Never merge an "
                "unreviewed research branch into a final report. Analysis may precede diagnosis. "
                "diagnosis_agent also verifies factual answers: even a simple FAQ or lookup "
                "requires it, not just incident diagnosis. Never skip the verification task "
                "because the user is asking a factual question. "
                f"ALLOWED_AGENTS: {allowed}\nSCHEMA: {StructuredPlan.model_json_schema()}\n"
                f"OBJECTIVE: {objective!r}\n{correction}"
            )
            raw = ""
            try:
                raw = await self.model.generate(prompt, StructuredPlan.model_json_schema())
                plan = StructuredPlan.model_validate_json(raw)
                validate_review_paths(plan)
                return plan
            except (ValidationError, ValueError) as exc:
                attempts.append({"raw_output": raw, "error": str(exc)})
                LOGGER.warning("Planner attempt=%d invalid: %s", len(attempts), str(exc)[:300])
                correction = f"PREVIOUS_OUTPUT_INVALID: {exc}. Correct every validation error."
        raise PlannerValidationError(attempts)


def validate_review_paths(plan: StructuredPlan) -> None:
    """Ensure each output branch passes Critic without replacing the LLM's DAG."""
    if plan.tasks[0].agent != AgentName.research_agent:
        raise ValueError("Execution must start with evidence research")
    reviewed: dict[str, bool] = {}
    for task in plan.tasks:
        if task.agent != AgentName.research_agent and not task.dependencies:
            raise ValueError("Specialists require dependency evidence")
        if task.agent == AgentName.diagnosis_agent:
            reviewed[task.task_id] = True
        elif task.agent == AgentName.research_agent:
            reviewed[task.task_id] = False  # New retrieval always needs review.
        else:
            reviewed[task.task_id] = all(reviewed[key] for key in task.dependencies)
    consumed = {key for task in plan.tasks for key in task.dependencies}
    if any(not checked for key, checked in reviewed.items() if key not in consumed):
        raise ValueError("Every terminal answer branch must pass diagnosis/Critic review")
