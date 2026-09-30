import asyncio

from agents.research import FixedResearchWorkflow
from evaluation.factory import build_advanced, build_tools
from models.llm import ScriptedModel


def test_react_stops_after_internal_answer() -> None:
    _, _, agent, _ = build_advanced()
    run = asyncio.run(agent.run("What is the Lambda timeout range?"))
    assert [step.action for step in run.steps] == ["rag_search"]
    assert run.metrics.tool_calls == 1
    assert run.metrics.llm_calls == 1
    assert run.response.sources


def test_react_continues_to_search_after_insufficient_first_result() -> None:
    _, _, agent, _ = build_advanced()
    run = asyncio.run(agent.run("How do I investigate EKS CrashLoopBackOff?"))
    assert [step.action for step in run.steps] == ["rag_search", "search"]
    assert run.metrics.tool_calls == 2
    assert run.metrics.llm_calls == 2
    assert any(source.document_id == "web-eks-crashloop" for source in run.response.sources)


def test_fixed_workflow_always_calls_all_tools() -> None:
    rag, search, documents = build_tools()
    run = asyncio.run(
        FixedResearchWorkflow(rag, search, documents).run("What is the Lambda timeout range?")
    )
    assert run.metrics.tool_calls == 3
    assert len(run.steps) == 3


def test_invalid_document_id_recovers_through_search() -> None:
    model = ScriptedModel([
        {"action": "read_document", "argument": "EKS CrashLoopBackOff",
         "reason": "Read this topic"},
        {"action": "finish", "reason": "Sufficient evidence"},
    ])
    _, _, agent, _ = build_advanced(model)
    run = asyncio.run(agent.run("How do I investigate EKS CrashLoopBackOff?"))
    assert [step.action for step in run.steps] == ["rag_search", "search"]
    assert "Recovery" in run.steps[1].reason
    assert any(source.document_id == "web-eks-crashloop" for source in run.response.sources)


def test_premature_finish_searches_before_refusal() -> None:
    model = ScriptedModel([
        {"action": "finish", "reason": "Nothing in internal retrieval"},
        {"action": "finish", "reason": "Still no evidence"},
    ])
    _, _, agent, _ = build_advanced(model)
    run = asyncio.run(agent.run("What is the DynamoDB global table limit?"))
    assert run.stop_reason == "no_evidence"
    assert run.metrics.tool_calls == 2
    assert not run.response.sources
