import asyncio

from rag.techqa.data import question_text, questions

from agents.critic import CriticLoop, LLMCritic
from models.llm import ScriptedModel
from models.schemas import CriticIssue, CriticResult


def test_current_pass_does_not_resolve_an_issue_without_specific_repair_proof():
    row = questions("fixture")[0]
    quote = row["QUESTION_TITLE"]
    issue = CriticIssue(code="missing_steps", description="The procedure is incomplete",
                        suggestion="Supply all procedure steps")
    model = ScriptedModel([{"resolutions": [{"issue_id": issue.code, "resolved": True,
        "source_ids": ["1"], "evidence_quote": "invented proof", "answer_quote": "invented proof",
        "remaining_problem": "Procedure still lacks the missing step"}]}])
    result = asyncio.run(LLMCritic(model).verify_issues(question_text(row), "[1] " + quote,
        quote + " [1]", [issue], CriticResult(passed=True, score=.9)))
    assert not result[0].resolved
    assert result[0].supporting_evidence_ids == []


def test_verified_specific_issue_records_actual_source_ids():
    row = questions("fixture")[0]
    quote = row["QUESTION_TITLE"]
    issue = CriticIssue(code="missing_context", description="The requested context is missing",
                        suggestion="State supplied context")
    model = ScriptedModel([{"resolutions": [{"issue_id": issue.code, "resolved": True,
        "source_ids": ["1"], "evidence_quote": quote, "answer_quote": quote,
        "remaining_problem": ""}]}])
    result = asyncio.run(LLMCritic(model).verify_issues(question_text(row), "[1] " + quote,
        quote + " [1]", [issue], CriticResult(passed=True, score=.9)))
    assert result[0].resolved and result[0].supporting_evidence_ids == ["1"]


def test_loop_blocks_publication_when_later_pass_has_unresolved_previous_issue():
    row = questions("fixture")[0]
    evidence = "[1] " + row["QUESTION_TITLE"]

    class Diagnosis:
        async def run(self, task, evidence, previous="", feedback=None, source_context=None):
            return evidence

    class Critic(LLMCritic):
        count = 0

        async def run(self, task, evidence, diagnosis, source_context=None):
            self.count += 1
            return (CriticResult(passed=False, score=.2, issues=[CriticIssue(
                code="not_repaired", description="The required step is absent",
                suggestion="Add the missing step")]) if self.count == 1
                else CriticResult(passed=True, score=.9))

    wire = {"resolutions": [{"issue_id": "not_repaired", "resolved": False,
        "source_ids": [], "evidence_quote": "", "answer_quote": "",
        "remaining_problem": "The required step is still absent"}]}
    result = asyncio.run(CriticLoop(Diagnosis(), Critic(ScriptedModel([wire])),
                                   max_retries=1).run(question_text(row), evidence))
    assert not result.passed and result.retries == 1
    assert not result.attempts[-1].issue_resolutions[0].resolved
    assert result.attempts[-1].resolved_previous_issues == []
