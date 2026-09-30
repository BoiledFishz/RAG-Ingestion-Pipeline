"""Task 3: Diagnosis -> Critic -> feedback -> revised Diagnosis, max two retries."""

from __future__ import annotations

import logging
import re
import time

from models.llm import MeteredModel, StructuredModel
from models.schemas import (
    CriticAttempt,
    CriticIssue,
    CriticLoopRun,
    CriticResult,
    DiagnosisDraft,
    Metrics,
)

LOGGER = logging.getLogger(__name__)


class LLMDiagnosisAgent:
    def __init__(self, model: StructuredModel) -> None:
        self.model = model

    async def run(
        self,
        task: str,
        evidence: str,
        previous: str = "",
        feedback: list[CriticIssue] | None = None,
    ) -> str:
        allowed = sorted(set(re.findall(r"\[(\d+)\]", evidence)) or {"evidence"})
        schema = DiagnosisDraft.model_json_schema()
        schema["properties"]["citations"]["items"] = {"type": "string", "enum": allowed}
        prompt = (
            "KIND: DIAGNOSIS\nAnswer the user's actual question directly using only EVIDENCE. "
            "State concrete supported facts and cite [1], [2] as supplied (or [evidence] for "
            "unlabelled evidence). Do not replace the answer with generic advice. "
            "Verify critic feedback against the evidence before applying it: the critic can be "
            "wrong. Do not copy issue codes into the answer or propose changing source documents. "
            "Preserve correct facts from the previous answer and fix only substantiated issues. "
            "Return the supporting evidence IDs in the required citations array. "
            "Return only JSON.\n"
            f"SCHEMA: {schema}\n"
            f"TASK: {task!r}\nEVIDENCE: {evidence!r}\n"
            f"PREVIOUS_DIAGNOSIS: {previous!r}\n"
            f"CRITIC_FEEDBACK: {[item.model_dump() for item in feedback or []]}"
        )
        draft = DiagnosisDraft.model_validate_json(
            await self.model.generate(prompt, schema)
        )
        references = " ".join(f"[{identifier}]" for identifier in draft.citations)
        return f"{draft.diagnosis} {references}"


class LLMCritic:
    def __init__(self, model: StructuredModel) -> None:
        self.model = model

    async def run(self, task: str, evidence: str, diagnosis: str) -> CriticResult:
        prompt = (
            "KIND: CRITIC\nEvaluate DIAGNOSIS against TASK and EVIDENCE, not this prompt. "
            "Pass a direct answer that includes the requested supported facts. Do not demand "
            "troubleshooting actions for a factual question or treat equivalent units as errors. "
            "Issue codes belong in YOUR output, not in the diagnosis you are reviewing. "
            "Do not invent deficiencies in the source documents. Every failing issue must name "
            "a specific wrong or missing factual claim and the supporting evidence. "
            "Use a stable issue code when the same issue remains. If there is no factual or "
            "question-completeness issue, return passed=true, issues=[] and a high score. "
            "Return only JSON.\n"
            f"SCHEMA: {CriticResult.model_json_schema()}\nTASK: {task!r}\n"
            f"EVIDENCE: {evidence!r}\nDIAGNOSIS: {diagnosis!r}"
        )
        return CriticResult.model_validate_json(
            await self.model.generate(prompt, CriticResult.model_json_schema())
        )


class CriticLoop:
    def __init__(
        self,
        diagnosis: LLMDiagnosisAgent,
        critic: LLMCritic,
        model_meter: MeteredModel | None = None,
        max_retries: int = 2,
    ) -> None:
        if not 0 <= max_retries <= 2:
            raise ValueError("max_retries cannot exceed two")
        self.diagnosis, self.critic = diagnosis, critic
        self.model_meter, self.max_retries = model_meter, max_retries

    async def run(self, task: str, evidence: str) -> CriticLoopRun:
        started = time.perf_counter()
        before = self.model_meter.snapshot() if self.model_meter else Metrics()
        attempts: list[CriticAttempt] = []
        previous = ""
        feedback: list[CriticIssue] = []
        for index in range(self.max_retries + 1):
            diagnosis = await self.diagnosis.run(task, evidence, previous, feedback)
            critique = await self.critic.run(task, evidence, diagnosis)
            allowed = set(re.findall(r"\[(\d+)\]", evidence)) or {"evidence"}
            cited = set(re.findall(r"\[(?:S)?(\d+|evidence)\]", diagnosis))
            if not cited or not cited <= allowed:
                LOGGER.warning("Critic citation validation failed at attempt %d", index + 1)
                issues = [issue for issue in critique.issues if issue.code != "invalid_citation"]
                issues.append(CriticIssue(
                    code="invalid_citation", description="Missing or nonexistent evidence citation",
                    suggestion="Preserve supported facts and cite only "
                    + ", ".join(f"[{identifier}]" for identifier in sorted(allowed)),
                ))
                critique = CriticResult(passed=False, score=min(critique.score, 0.5), issues=issues)
            current_codes = {issue.code for issue in critique.issues}
            resolved = [issue.code for issue in feedback if issue.code not in current_codes]
            attempts.append(
                CriticAttempt(
                    attempt=index + 1,
                    diagnosis=diagnosis,
                    critique=critique,
                    resolved_previous_issues=resolved,
                )
            )
            previous = diagnosis
            if critique.passed:
                break
            feedback = critique.issues
        measured = self.model_meter.delta(before) if self.model_meter else Metrics()
        measured.latency_ms = (time.perf_counter() - started) * 1000
        return CriticLoopRun(
            final_diagnosis=previous,
            passed=attempts[-1].critique.passed,
            retries=len(attempts) - 1,
            attempts=attempts,
            metrics=measured,
        )
