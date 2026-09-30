import asyncio

from agents.critic import CriticLoop, LLMCritic, LLMDiagnosisAgent
from models.llm import MeteredModel, ScriptedModel


def test_critic_feedback_is_applied_and_issue_resolved() -> None:
    scripted = ScriptedModel(
        [
            {"diagnosis": "The service is probably misconfigured.", "citations": ["evidence"]},
            {
                "passed": False,
                "score": 0.4,
                "issues": [
                    {
                        "code": "missing_evidence",
                        "description": "The claim has no cited evidence",
                        "suggestion": "Tie the diagnosis to the timeout evidence",
                    }
                ],
            },
            {"diagnosis": "Evidence states the timeout is 1 through 900 seconds.",
             "citations": ["evidence"]},
            {"passed": True, "score": 0.95, "issues": []},
        ]
    )
    meter = MeteredModel(scripted)
    loop = CriticLoop(LLMDiagnosisAgent(meter), LLMCritic(meter), meter)
    run = asyncio.run(loop.run("Diagnose timeout", "Timeout range is 1 through 900 seconds"))
    assert run.passed
    assert run.retries == 1
    assert run.attempts[1].resolved_previous_issues == ["missing_evidence"]
    assert "missing_evidence" in scripted.prompts[2]
    assert run.metrics.llm_calls == 4


def test_critic_never_retries_more_than_twice() -> None:
    outputs = []
    for index in range(3):
        outputs.extend(
            [
                {"diagnosis": f"Unresolved diagnosis attempt {index + 1}",
                 "citations": ["evidence"]},
                {
                    "passed": False,
                    "score": 0.2,
                    "issues": [
                        {
                            "code": "still_wrong",
                            "description": "The diagnosis is still unsupported",
                            "suggestion": "Use the supplied evidence",
                        }
                    ],
                },
            ]
        )
    meter = MeteredModel(ScriptedModel(outputs))
    run = asyncio.run(
        CriticLoop(LLMDiagnosisAgent(meter), LLMCritic(meter), meter).run("Diagnose", "Evidence")
    )
    assert not run.passed
    assert run.retries == 2
    assert len(run.attempts) == 3
    assert run.metrics.llm_calls == 6


def test_critic_cannot_pass_a_nonexistent_citation_without_repair() -> None:
    scripted = ScriptedModel([
        {"diagnosis": "Lambda supports 1 to 900 seconds.", "citations": ["7"]},
        {"passed": True, "score": 1, "issues": []},
        {"diagnosis": "Lambda supports 1 to 900 seconds.", "citations": ["1"]},
        {"passed": True, "score": 1, "issues": []},
    ])
    meter = MeteredModel(scripted)
    run = asyncio.run(CriticLoop(LLMDiagnosisAgent(meter), LLMCritic(meter), meter).run(
        "What is the Lambda timeout range?", "[1] Lambda supports 1 to 900 seconds.",
    ))
    assert run.passed and run.retries == 1
    assert run.attempts[0].critique.issues[0].code == "invalid_citation"
    assert "invalid_citation" in run.attempts[1].resolved_previous_issues
