import asyncio

from rag.techqa.data import questions

from agents.critic import CriticLoop, LLMCritic, LLMDiagnosisAgent
from models.llm import MeteredModel, ScriptedModel


def test_dependency_timeout_is_recorded_without_claiming_critic_success():
    import httpx

    class TimeoutModel:
        async def generate(self, prompt, schema):
            raise httpx.ReadTimeout("injected model outage")

    meter = MeteredModel(TimeoutModel())
    run = asyncio.run(
        CriticLoop(LLMDiagnosisAgent(meter), LLMCritic(meter), meter).run(
            "Review the supported configuration",
            "[1] streamtool setproperty",
        )
    )
    assert not run.passed
    assert len(run.attempts) == 1
    assert any(issue.code == "model_unavailable" for issue in run.attempts[0].critique.issues)


def test_invalid_citation_can_be_added_when_critic_returns_maximum_issues():
    model = MeteredModel(ScriptedModel([
        {"diagnosis": questions("fixture")[0]["ANSWER"], "citations": ["7"]},
        {"passed": False, "score": 0.2, "issues": [
            {"code": f"issue_{i}", "description": "Injected issue", "suggestion": "Use evidence"}
            for i in range(3)
        ]},
    ]))
    run = asyncio.run(CriticLoop(
        LLMDiagnosisAgent(model), LLMCritic(model), model, max_retries=0
    ).run("Review evidence", "[1] " + questions("fixture")[0]["ANSWER"]))
    assert not run.passed
    assert len(run.attempts[0].critique.issues) == 3
    assert run.attempts[0].critique.issues[-1].code == "invalid_citation"


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
                        "suggestion": "Tie the diagnosis to the TechQA evidence",
                    }
                ],
            },
            {
                "diagnosis": questions("fixture")[0]["ANSWER"],
                "citations": ["evidence"],
            },
            {"passed": True, "score": 0.95, "issues": []},
        ]
    )
    meter = MeteredModel(scripted)
    loop = CriticLoop(LLMDiagnosisAgent(meter), LLMCritic(meter), meter)
    run = asyncio.run(loop.run(
        questions("fixture")[0]["QUESTION_TITLE"], questions("fixture")[0]["ANSWER"]
    ))
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
                {
                    "diagnosis": f"Unresolved diagnosis attempt {index + 1}",
                    "citations": ["evidence"],
                },
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
    scripted = ScriptedModel(
        [
            {"diagnosis": questions("fixture")[0]["ANSWER"], "citations": ["7"]},
            {"passed": True, "score": 1, "issues": []},
            {"diagnosis": questions("fixture")[0]["ANSWER"], "citations": ["1"]},
            {"passed": True, "score": 1, "issues": []},
        ]
    )
    meter = MeteredModel(scripted)
    run = asyncio.run(
        CriticLoop(LLMDiagnosisAgent(meter), LLMCritic(meter), meter).run(
            "How are Streams environment variables set after upgrade to 4.1.1.2?",
            "[1] " + questions("fixture")[0]["ANSWER"],
        )
    )
    assert run.passed and run.retries == 1
    assert run.attempts[0].critique.issues[0].code == "invalid_citation"
    assert "invalid_citation" in run.attempts[1].resolved_previous_issues
