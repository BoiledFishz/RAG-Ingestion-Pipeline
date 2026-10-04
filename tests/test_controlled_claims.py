import asyncio
import json

import pytest

from rag.techqa.claims import ComposedAnswer, audit_claims, compose_answer, compose_checked_answer
from rag.techqa.data import documents, question_text, questions
from rag.techqa.facts import required_facts


class Outputs:
    def __init__(self, *values):
        self.values = list(values)

    async def generate(self, prompt, schema):
        return json.dumps(self.values.pop(0))


def fixture():
    row = next(q for q in questions("fixture") if q["QUESTION_ID"] == "TRAIN_Q011")
    doc = next(d for d in documents("fixture") if d["id"] == row["DOCUMENT"])
    query = question_text(row)
    return query, doc["text"], [f.key for f in required_facts(query)]


def wire(text, quote, keys):
    return {"claims": [{"text": text, "source_id": "1", "exact_quote": quote}],
            "covered_facts": keys, "missing_facts": [], "status": "complete"}


def test_command_and_inline_code_mutation_is_rejected():
    query, evidence, keys = fixture()
    quote = "sudo chown -R root:admin 25"
    assert quote in evidence
    for text in ["sudo chown -R root:admin 26", "Run `sudo chown -R root:admin 26`.",
                 "3. sudo chown -R root:admin 26"]:
        with pytest.raises(ValueError, match="Command syntax|Inline command"):
            asyncio.run(compose_answer(Outputs(wire(text, quote, keys)), query, {"1": evidence}))


def test_invented_version_or_source_id_is_rejected():
    query, evidence, keys = fixture()
    quote = "sudo chown -R root:admin 25"
    with pytest.raises(ValueError, match="critical literal"):
        asyncio.run(compose_answer(Outputs(wire("This applies to version 25.9.9.", quote, keys)),
                                   query, {"1": evidence}))
    value = wire(quote, quote, keys)
    value["claims"][0]["source_id"] = "7"
    with pytest.raises(ValueError, match="supplied source"):
        asyncio.run(compose_answer(Outputs(value), query, {"1": evidence}))


def test_independent_audit_downgrades_self_reported_complete_answer():
    query, evidence, keys = fixture()
    quote = "sudo chown -R root:admin 25"
    audit = {"principal_request": "Activate existing product on a new host",
             "required_facts": keys, "covered_facts": [], "missing_facts": keys,
             "incorrect_facts": [], "fact_evidence": [], "verdict": "revise"}
    claim_audit = {"c0": {"supported": True, "quote_id": "c0_0", "reason": "Exact command"}}
    result = asyncio.run(compose_checked_answer(Outputs(wire(quote, quote, keys),
                                                        claim_audit, audit),
                                                query, {"1": evidence}))
    assert result.status == "partial" and result.missing_facts == keys
    assert result.render().startswith("部分信息")


def test_missing_fact_cannot_be_marked_complete():
    query, evidence, keys = fixture()
    quote = "sudo chown -R root:admin 25"
    value = wire(quote, quote, keys)
    value.update(covered_facts=keys[:1], missing_facts=keys[1:])
    with pytest.raises(ValueError, match="status conflicts"):
        asyncio.run(compose_answer(Outputs(value), query, {"1": evidence}))


def test_claim_proof_cannot_use_another_claims_source_catalog():
    query, evidence, keys = fixture()
    quote = "sudo chown -R root:admin 25"
    value = wire(quote, quote, keys)
    value["claims"].append({"text": quote, "source_id": "2", "exact_quote": quote})
    composed = ComposedAnswer.model_validate(value)
    checks = {"c0": {"supported": True, "quote_id": "c1_0", "reason": "Other source"},
              "c1": {"supported": True, "quote_id": "c1_0", "reason": "Own source"}}
    with pytest.raises(ValueError, match="entailment failed"):
        asyncio.run(audit_claims(Outputs(checks), query, composed, {"1": evidence, "2": evidence}))
