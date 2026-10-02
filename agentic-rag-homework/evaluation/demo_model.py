"""Deterministic structured-output simulator for repeatable, no-network experiments."""

from __future__ import annotations

import ast
import json
import re
from typing import Any


class DemoStructuredModel:
    @staticmethod
    def excerpt(evidence: str) -> str:
        """Keep the test double inside the diagnosis schema's output budget."""
        return evidence if len(evidence) <= 1800 else evidence[:1800].rsplit(" ", 1)[0]

    @staticmethod
    def field(prompt: str, name: str) -> str:
        line = next(line for line in prompt.splitlines() if line.startswith(name + ": "))
        return str(ast.literal_eval(line.split(": ", 1)[1]))

    async def generate(self, prompt: str, schema: dict[str, Any]) -> str:
        if "KIND: PLANNER" in prompt:
            return json.dumps(
                {
                    "tasks": [
                        {
                            "task_id": "T001",
                            "agent": "research_agent",
                            "objective": "Collect evidence relevant to the requested investigation",
                            "dependencies": [],
                        },
                        {
                            "task_id": "T002",
                            "agent": "diagnosis_agent",
                            "objective": (
                                "Produce an evidence-grounded diagnosis and recommendation"
                            ),
                            "dependencies": ["T001"],
                        },
                        {
                            "task_id": "T003",
                            "agent": "report_writer",
                            "objective": "Return the checked result with explicit sources",
                            "dependencies": ["T002"],
                        },
                    ]
                }
            )
        if "KIND: REACT" in prompt:
            # A unit-test model double, with no product-specific knowledge or answers.
            return json.dumps(
                {
                    "action": "finish",
                    "argument": "",
                    "reason": "Inspect existing evidence; runtime validates support",
                }
            )
        if "KIND: DIAGNOSIS" in prompt:
            repaired = "CRITIC_FEEDBACK: []" not in prompt
            evidence = self.field(prompt, "EVIDENCE")
            excerpt = self.excerpt(evidence)
            diagnosis = (
                excerpt + ("" if re.search(r"\[\d+\]", excerpt) else " [evidence]")
                if repaired
                else "Check the related configuration."
            )
            citations = list(dict.fromkeys(re.findall(r"\[(\d+)\]", excerpt)))[:4] or ["evidence"]
            return json.dumps({"diagnosis": diagnosis, "citations": citations}, ensure_ascii=False)
        if "KIND: CRITIC" in prompt:
            evidence = self.field(prompt, "EVIDENCE")
            diagnosis = self.field(prompt, "DIAGNOSIS")

            def clean(value: str) -> str:
                return re.sub(r"\[(?:\d+|evidence)\]", "", value).strip()

            if clean(self.excerpt(evidence)) in clean(diagnosis) and re.search(
                r"\[(?:\d+|evidence)\]",
                diagnosis,
            ):
                return json.dumps({"passed": True, "score": 0.9, "issues": []})
            return json.dumps(
                {
                    "passed": False,
                    "score": 0.45,
                    "issues": [
                        {
                            "code": "missing_evidence",
                            "description": "The diagnosis does not cite retrieved evidence",
                            "suggestion": "Cite evidence and provide verifiable checks",
                        }
                    ],
                },
                ensure_ascii=False,
            )
        raise ValueError("unknown prompt kind")
