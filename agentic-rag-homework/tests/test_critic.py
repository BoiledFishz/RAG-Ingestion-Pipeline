import asyncio

from rag.techqa.data import questions

from agents.critic import (
    INSUFFICIENT_DIAGNOSIS,
    CriticLoop,
    LLMCritic,
    LLMDiagnosisAgent,
    LLMGroundedDiagnosisAgent,
)
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
    assert not run.answer_sufficient
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
    assert not run.answer_sufficient
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


def test_paraphrased_issue_is_not_reported_as_resolved():
    outputs = []
    for description in ["A requested fact is missing", "The answer omits a requested fact"]:
        outputs.extend([
            {"diagnosis": questions("fixture")[0]["ANSWER"], "citations": ["1"]},
            {"verdict": "revise", "issues": [description]},
        ])
    meter = MeteredModel(ScriptedModel(outputs))
    run = asyncio.run(CriticLoop(
        LLMDiagnosisAgent(meter), LLMCritic(meter), meter, max_retries=1,
    ).run("Review the official answer", "[1] " + questions("fixture")[0]["ANSWER"]))
    assert not run.passed
    assert run.attempts[1].resolved_previous_issues == []


def test_contradictory_flat_critic_verdict_is_rejected():
    import pytest
    from pydantic import ValidationError

    critic = LLMCritic(ScriptedModel([{"verdict": "pass", "issues": ["Missing fact"]}]))
    with pytest.raises(ValidationError):
        asyncio.run(critic.run("Review", questions("fixture")[0]["ANSWER"], "Diagnosis [1]"))


def test_critic_cannot_approve_an_invented_error_code():
    model = MeteredModel(ScriptedModel([
        {"diagnosis": "The Streams issue produces SQL99999N.", "citations": ["1"]},
        {"verdict": "pass", "issues": []},
    ]))
    run = asyncio.run(CriticLoop(
        LLMDiagnosisAgent(model), LLMCritic(model), model, max_retries=0,
    ).run("Review the Streams issue", "[1] " + questions("fixture")[0]["ANSWER"]))
    assert not run.passed
    assert run.attempts[0].critique.issues[-1].code == "unsupported_identifier"


def test_production_diagnosis_only_renders_original_evidence():
    original = questions("fixture")[0]
    agent = LLMGroundedDiagnosisAgent(ScriptedModel([
        {"sufficient": True, "source_ids": ["1"]},
    ]))
    diagnosis = asyncio.run(agent.run(original["QUESTION_TITLE"], "[1] " + original["ANSWER"]))
    assert diagnosis == original["ANSWER"].strip() + " [1]"


def test_production_diagnosis_rejects_unknown_source_id():
    import pytest

    original = questions("fixture")[0]
    agent = LLMGroundedDiagnosisAgent(ScriptedModel([
        {"sufficient": True, "source_ids": ["7"]},
    ]))
    with pytest.raises(ValueError, match="Unknown"):
        asyncio.run(agent.run(original["QUESTION_TITLE"], "[1] " + original["ANSWER"]))


def test_validated_refusal_is_distinct_from_a_sufficient_answer():
    original = questions("fixture")[0]
    meter = MeteredModel(ScriptedModel([
        {"sufficient": False, "source_ids": []},
        {"sufficient": False, "source_ids": []},
    ]))
    loop = CriticLoop(LLMGroundedDiagnosisAgent(meter), LLMCritic(meter), meter)
    run = asyncio.run(loop.run(original["QUESTION_TITLE"], "[1] " + original["ANSWER"]))
    assert run.passed and not run.answer_sufficient
    assert run.final_diagnosis.startswith(INSUFFICIENT_DIAGNOSIS)


def test_critic_repairs_refusal_when_independent_review_finds_real_answer():
    original = questions("fixture")[0]
    scripted = ScriptedModel([
        {"sufficient": False, "source_ids": []},
        {"sufficient": True, "source_ids": ["1"]},
        {"sufficient": True, "source_ids": ["1"]},
        {"sufficient": True, "source_ids": ["1"]},
    ])
    meter = MeteredModel(scripted)
    run = asyncio.run(CriticLoop(
        LLMGroundedDiagnosisAgent(meter), LLMCritic(meter), meter,
    ).run(original["QUESTION_TITLE"], "[1] " + original["ANSWER"]))
    assert run.passed and run.answer_sufficient and run.retries == 1
    assert run.attempts[0].critique.issues[0].code == "supported_answer_refused"
    assert run.attempts[1].resolved_previous_issues == ["supported_answer_refused"]
    assert original["ANSWER"].strip() in run.final_diagnosis


def test_production_critic_only_reviews_cited_evidence_and_its_provenance():
    first, unrelated = questions("fixture")[:2]
    scripted = ScriptedModel([
        {"sufficient": True, "source_ids": ["1"]},
        {"sufficient": True, "source_ids": ["1"]},
    ])
    meter = MeteredModel(scripted)
    run = asyncio.run(CriticLoop(
        LLMGroundedDiagnosisAgent(meter), LLMCritic(meter), meter,
    ).run(first["QUESTION_TITLE"], f"[1] {first['ANSWER']}\n[2] {unrelated['ANSWER']}",
          source_context={"1": {"title": first["QUESTION_TITLE"]},
                          "2": {"title": unrelated["QUESTION_TITLE"]}}))
    assert run.passed and run.answer_sufficient
    assert "streamtool setproperty" in scripted.prompts[1]
    assert "Exit() parser function" not in scripted.prompts[1]
    assert unrelated["QUESTION_TITLE"] not in scripted.prompts[1]


def test_refusal_review_checks_later_batches_before_approving_abstention():
    rows = [row for row in questions("fixture") if row["ANSWERABLE"] == "Y"][:5]
    scripted = ScriptedModel([
        {"sufficient": False, "source_ids": []},
        {"sufficient": False, "source_ids": []},
        {"sufficient": False, "source_ids": []},
        {"sufficient": True, "source_ids": ["5"]},
        {"sufficient": False, "source_ids": []},
        {"sufficient": True, "source_ids": ["5"]},
        {"sufficient": True, "source_ids": ["5"]},
    ])
    meter = MeteredModel(scripted)
    run = asyncio.run(CriticLoop(
        LLMGroundedDiagnosisAgent(meter), LLMCritic(meter), meter,
    ).run(rows[-1]["QUESTION_TITLE"], "\n".join(
        f"[{i}] {row['ANSWER']}" for i, row in enumerate(rows, 1)
    )))
    assert run.passed and run.answer_sufficient and run.retries == 1
    assert rows[-1]["ANSWER"].strip() in run.final_diagnosis
    assert meter.metrics.llm_calls == 7
