import asyncio
import json
from pathlib import Path

from rag.techqa.data import question_text, questions

from agents.critic import CriticLoop, LLMCritic
from models.llm import ScriptedModel
from models.schemas import CriticIssue, CriticResult, IssueResolution


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


def condition_case():
    path = Path("evaluation/results/techqa_critic_components_20261003-01/cases.json")
    return next(row for row in json.loads(path.read_text(encoding="utf-8"))
                if row["case"] == "missing_exposure_condition")


def run_issue_history(repaired):
    case = condition_case()

    class Diagnosis:
        count = 0

        async def run(self, task, evidence, previous="", feedback=None, source_context=None):
            self.count += 1
            return (case["evidence"][4:] + " [1]" if repaired and self.count > 1
                    else case["answer"])

    class Critic(LLMCritic):
        def __init__(self):
            super().__init__(ScriptedModel([]))
            self.count = 0
            self.checked = []

        async def run(self, task, evidence, diagnosis, source_context=None):
            self.count += 1
            if self.count < 3:
                code = "missing_condition" if self.count == 1 else "invalid_model_output"
                return CriticResult(passed=False, score=.2, issues=[CriticIssue(
                    code=code, description=case["known_defect"] if self.count == 1
                    else "Protocol repair pending", suggestion="Verify the outstanding issue")])
            return CriticResult(passed=True, score=.9)

        async def verify_issues(self, task, evidence, diagnosis, feedback, critique):
            self.checked.append([i.code for i in feedback])
            return [IssueResolution(issue_id=i.code, description=i.description,
                resolved=repaired or i.code == "invalid_model_output",
                supporting_evidence_ids=["1"] if repaired or i.code == "invalid_model_output"
                else [], remaining_problem="" if repaired or i.code == "invalid_model_output"
                else i.description) for i in feedback]

    critic = Critic()
    result = asyncio.run(CriticLoop(Diagnosis(), critic).run(case["query"], case["evidence"]))
    return result, critic.checked


def test_protocol_error_cannot_erase_an_unresolved_earlier_defect():
    result, checked = run_issue_history(False)
    assert not result.passed and result.retries == 2
    assert checked[-1] == ["missing_condition", "invalid_model_output"]
    assert "missing_condition" not in result.attempts[-1].resolved_previous_issues


def test_proven_prior_repair_can_leave_the_pending_issue_ledger():
    result, checked = run_issue_history(True)
    assert result.passed and result.retries == 2
    assert checked[-1] == ["invalid_model_output"]
    assert "missing_condition" in result.attempts[1].resolved_previous_issues


def test_unrelated_exact_quote_cannot_clear_a_missing_version_condition():
    case = condition_case()
    quote = case["evidence"][4:104]
    issue = CriticIssue(code="condition_missing",
        description="Missing required fact: affected_versions", suggestion="Retain conditions")
    model = ScriptedModel([{"resolutions": [{"issue_id": issue.code, "resolved": True,
        "source_ids": ["1"], "evidence_quote": quote, "answer_quote": quote,
        "remaining_problem": ""}]}])
    result = asyncio.run(LLMCritic(model).verify_issues(case["query"], case["evidence"],
        case["answer"], [issue], CriticResult(passed=False, score=0, issues=[CriticIssue(
            code="invalid_model_output", description="Output validation failed",
            suggestion="Repair output protocol")])))
    assert not result[0].resolved and not result[0].supporting_evidence_ids
