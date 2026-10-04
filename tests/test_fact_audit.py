import asyncio
import json

import pytest

from rag.techqa.claims import audit_requirements
from rag.techqa.data import documents, question_text, questions
from rag.techqa.facts import required_facts


class Output:
    def __init__(self, value):
        self.value = value

    async def generate(self, prompt, schema):
        return json.dumps(self.value)


def test_source_only_content_cannot_establish_actual_answer_coverage():
    row = questions("fixture")[0]
    doc = next(d for d in documents("fixture") if d["id"] == row["DOCUMENT"])
    keys = [f.key for f in required_facts(question_text(row))]
    quote = doc["text"][:100]
    wire = dict(principal_request=row["QUESTION_TITLE"], required_facts=keys,
                covered_facts=keys, missing_facts=[], incorrect_facts=[], verdict="pass",
                fact_evidence=[dict(fact=keys[0], source_id="1", evidence_quote=quote,
                                    answer_quote=quote)])
    with pytest.raises(ValueError, match="actual-answer"):
        asyncio.run(audit_requirements(Output(wire), question_text(row),
                                        "Insufficient evidence", {"1": doc["text"]}))


def test_covered_fact_requires_exact_support_and_unknown_sources_fail():
    row = questions("fixture")[0]
    keys = [f.key for f in required_facts(question_text(row))]
    wire = dict(principal_request=row["QUESTION_TITLE"], required_facts=keys,
                covered_facts=keys, missing_facts=[], incorrect_facts=[], verdict="pass",
                fact_evidence=[dict(fact=keys[0], source_id="7", evidence_quote="Missing",
                                    answer_quote="Missing")])
    with pytest.raises(ValueError, match="source AND"):
        asyncio.run(audit_requirements(Output(wire), question_text(row), "Missing",
                                        {"1": "Missing"}))


def test_missing_required_fact_cannot_be_overridden_by_model_pass():
    row = next(q for q in questions("fixture") if q["QUESTION_ID"] == "TRAIN_Q006")
    keys = [f.key for f in required_facts(question_text(row))]
    wire = dict(principal_request=row["QUESTION_TITLE"], required_facts=keys,
                covered_facts=[], missing_facts=keys, incorrect_facts=[], verdict="pass",
                fact_evidence=[])
    with pytest.raises(ValueError, match="verdict"):
        asyncio.run(audit_requirements(Output(wire), question_text(row), "Refusal",
                                        {"1": "Refusal"}))


def test_already_owned_code_requires_activation_not_code_lookup():
    row = next(q for q in questions("fixture") if q["QUESTION_ID"] == "TRAIN_Q011")
    query = question_text(row)
    keys = [f.key for f in required_facts(query)]
    # Exact real evidence from the preserved native failure; the model double
    # intentionally mislabels coverage, exercising the generic premise guard.
    from pathlib import Path
    probe = json.loads(Path("audit/techqa_root_cause_20261003-01/"
                            "critic_baseline.json").read_text(encoding="utf-8"))
    case = next(r for r in probe["records"] if r["id"] == "TRAIN_Q011"
                and r["mode"] == "actual_selected_blocks")
    answer = case["diagnosis"]
    quote = answer[:80]
    wire = dict(principal_request=row["QUESTION_TITLE"], required_facts=keys,
                covered_facts=keys, missing_facts=[], incorrect_facts=[], verdict="pass",
                fact_evidence=[dict(fact=f, source_id="1", evidence_quote=quote,
                                    answer_quote=quote) for f in keys])
    result = asyncio.run(audit_requirements(Output(wire), query, answer, {"1": answer}))
    assert result.verdict == "revise" and not result.covered_facts
    assert "activation_on_new_host" in result.missing_facts
