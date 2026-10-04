"""Integrity checks use original TechQA procedures and isolated component corruptions."""

import json
from pathlib import Path

from rag.techqa.claims import (
    FactAudit,
    FactSupport,
    copied_procedure_is_incomplete,
    copied_version_condition_is_missing,
    symptom_only_without_action,
    unsupported_commands,
    validate_audit,
)
from rag.techqa.facts import required_facts


def component_cases():
    path = Path("agentic-rag-homework/evaluation/results/"
                "techqa_critic_components_20261003-01/cases.json")
    return {row["case"]: row for row in json.loads(path.read_text(encoding="utf-8"))}


def test_copied_final_step_missing_and_complete_original_is_preserved():
    case = component_cases()["missing_last_step"]
    source = case["evidence"][4:]
    assert copied_procedure_is_incomplete(case["answer"], source)
    assert not copied_procedure_is_incomplete(source, source)


def test_original_commands_pass_and_adjacent_argument_is_rejected():
    case = component_cases()["adjacent_version"]
    assert unsupported_commands(case["answer"], case["evidence"])
    assert not unsupported_commands(case["evidence"], case["evidence"])


def test_component_alias_argument_changed_cannot_pass_as_source_command():
    case = component_cases()["wrong_component"]
    assert unsupported_commands(case["answer"], case["evidence"])
    assert not unsupported_commands(case["evidence"], case["evidence"])


def test_real_symptom_only_does_not_prove_configuration_and_actual_procedure_survives():
    cases = component_cases()
    assert symptom_only_without_action(cases["symptom_without_solution"]["answer"])
    assert symptom_only_without_action(cases["insufficient_evidence_refusal"]["evidence"][4:])
    assert not symptom_only_without_action(cases["wrong_component"]["evidence"][4:])


def test_copied_version_row_cannot_borrow_another_rows_exposure_condition():
    cases = component_cases()
    case = cases["missing_exposure_condition"]
    assert copied_version_condition_is_missing(case["answer"], case["evidence"][4:])
    correct = cases["correct_answer"]
    assert not copied_version_condition_is_missing(correct["answer"], correct["evidence"][4:])
    keys = [fact.key for fact in required_facts(case["query"])]
    source = case["evidence"][4:]
    review = FactAudit(principal_request=case["query"][:100], required_facts=keys,
        covered_facts=keys, missing_facts=[], incorrect_facts=[], verdict="pass",
        fact_evidence=[FactSupport(fact=key, source_id="1", evidence_quote=source[:100],
                                  answer_quote=case["answer"][:100]) for key in keys])
    result = validate_audit(review, case["query"], case["answer"], {"1": source})
    assert result.verdict == "revise" and "affected_versions" in result.missing_facts
    assert "affected_versions" not in result.covered_facts


def test_version_condition_guard_does_not_change_other_real_procedures():
    cases = component_cases()
    for key in ["missing_last_step", "adjacent_version", "wrong_component"]:
        assert not copied_version_condition_is_missing(cases[key]["answer"],
                                                        cases[key]["evidence"][4:])
