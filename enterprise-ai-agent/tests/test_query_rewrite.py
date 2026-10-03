from __future__ import annotations

import asyncio
from typing import Any

from agents.rag_agent.rewrite import LLMRewriter, RuleRewriter
from models.schemas import RewriteDecision


class FakeModel:
    def __init__(self, output: str) -> None:
        self.output = output

    async def generate(self, prompt: str, schema: dict[str, Any]) -> str:
        return self.output


def test_rewrite_synonyms_without_adding_a_cause() -> None:
    result = asyncio.run(RuleRewriter().rewrite("Please bring back my deleted configuration"))
    assert "restore" in result.query and "configuration" in result.query
    assert "version" not in result.query.casefold()


def test_ambiguous_query_requests_clarification() -> None:
    result = asyncio.run(RuleRewriter().rewrite("权限有问题，怎么办？"))
    assert result.action == "clarify"
    assert result.clarification


def test_llm_rewrite_cannot_drop_error_code_or_negation() -> None:
    fake = FakeModel(
        RewriteDecision(query="WebSphere startup").model_dump_json(exclude={"fallback"})
    )
    result = asyncio.run(LLMRewriter(fake).rewrite("WebSphere ADMU0111E without admin access"))
    assert result.fallback
    assert "ADMU0111E" in result.query and "without" in result.query


def test_llm_rewrite_valid_json_used() -> None:
    output = RewriteDecision(query="WebSphere ADMU0111E startup troubleshooting")
    result = asyncio.run(
        LLMRewriter(FakeModel(output.model_dump_json(exclude={"fallback"}))).rewrite(
            "Troubleshoot WebSphere ADMU0111E during startup"
        )
    )
    assert not result.fallback
    assert result.query == output.query


def test_llm_rewrite_malformed_output_falls_back() -> None:
    result = asyncio.run(
        LLMRewriter(FakeModel("not JSON")).rewrite("What causes WebSphere ADMU0111E?")
    )
    assert result.fallback and "ADMU0111E" in result.query


def test_specific_service_error_is_searched_before_asking_for_more_details() -> None:
    output = RewriteDecision(
        query="WebSphere ADMU0111E", action="clarify", clarification="Which version?"
    )
    result = asyncio.run(
        LLMRewriter(FakeModel(output.model_dump_json(exclude={"fallback"}))).rewrite(
            "How do I debug WebSphere ADMU0111E?"
        )
    )
    assert result.action == "retrieve" and result.fallback


def test_rule_rewrite_does_not_rename_files_to_objects() -> None:
    result = asyncio.run(RuleRewriter().rewrite("DB2 cannot read a local file"))
    assert "file" in result.query and "object" not in result.query


def test_official_versioned_socket_packages_are_searched_before_clarification() -> None:
    from rag.techqa.data import question_text, questions

    row = next(r for r in questions("regression") if r["QUESTION_ID"] == "DEV_Q007")
    query = question_text(row)
    output = RewriteDecision(query=query, action="clarify", clarification="Which version?")
    result = asyncio.run(LLMRewriter(
        FakeModel(output.model_dump_json(exclude={"fallback"})),
    ).rewrite(query))
    assert result.action == "retrieve" and result.fallback
    assert "nco-g-socket-java-2_0" in result.query and "nco-g-socket-10_0" in result.query
