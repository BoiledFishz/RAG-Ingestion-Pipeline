"""Task 1: an LLM planner whose output is schema- and DAG-validated."""

from __future__ import annotations

from pydantic import ValidationError

from models.llm import StructuredModel
from models.schemas import AgentName, StructuredPlan


class PlannerValidationError(RuntimeError):
    pass


class LLMPlanner:
    def __init__(self, model: StructuredModel, max_attempts: int = 2) -> None:
        self.model, self.max_attempts = model, max_attempts

    async def run(self, objective: str) -> StructuredPlan:
        if not objective.strip():
            raise ValueError("objective cannot be blank")
        allowed = ", ".join(item.value for item in AgentName)
        correction = ""
        for _ in range(self.max_attempts):
            prompt = (
                "KIND: PLANNER\nDecompose the objective into the smallest useful DAG and return "
                "only schema-valid JSON. IDs must be sequential T001, T002... Dependencies may "
                "reference only earlier IDs. Never invent an agent. "
                "research_agent retrieves evidence; data_analyst selects supporting facts from "
                "dependencies; diagnosis_agent diagnoses and performs a critic loop using only "
                "dependency evidence; report_writer composes the evidence-backed final answer. "
                "Start with research_agent. All other agents need dependencies carrying evidence. "
                "For an investigation, include diagnosis_agent, then report_writer. "
                f"ALLOWED_AGENTS: {allowed}\nSCHEMA: {StructuredPlan.model_json_schema()}\n"
                f"OBJECTIVE: {objective!r}\n{correction}"
            )
            try:
                raw = await self.model.generate(prompt, StructuredPlan.model_json_schema())
                return StructuredPlan.model_validate_json(raw)
            except (ValidationError, ValueError) as exc:
                correction = f"PREVIOUS_OUTPUT_INVALID: {exc}. Correct every validation error."
        raise PlannerValidationError("planner produced invalid output twice")
