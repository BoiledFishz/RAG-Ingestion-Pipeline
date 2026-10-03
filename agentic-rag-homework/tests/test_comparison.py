import asyncio

from agents.systems import MultiAgentVersion, SingleAgentVersion
from evaluation.factory import build_advanced


def test_multi_agent_records_extra_coordination_cost() -> None:
    _, _, single_research, _ = build_advanced()
    single = asyncio.run(
        SingleAgentVersion(single_research).run(
            "How are Streams environment variables set after upgrade to 4.1.1.2?"
        )
    )

    meter, planner, research, critic = build_advanced()
    multi = asyncio.run(
        MultiAgentVersion(planner, research, critic, meter).run(
            "How are Streams environment variables set after upgrade to 4.1.1.2?"
        )
    )
    assert {s.document_id for s in single.response.sources} == {
        s.document_id for s in multi.response.sources
    }
    assert multi.plan is not None
    assert multi.critic is not None and multi.critic.passed
    assert multi.metrics.llm_calls > single.metrics.llm_calls
    assert multi.metrics.token_usage > single.metrics.token_usage


def test_failed_critic_blocks_previous_answer_and_propagates_through_report():
    from rag.techqa.data import question_text, questions

    from agents.systems import REVIEW_FAILED
    from evaluation.run import quality
    from models.schemas import CriticAttempt, CriticIssue, CriticLoopRun, CriticResult, Metrics

    class RejectingCritic:
        async def run(self, task, evidence, source_context=None):
            rejection = CriticResult(passed=False, score=0, issues=[CriticIssue(
                code="injected_rejection", description="Evidence review failed",
                suggestion="Do not publish this answer",
            )])
            return CriticLoopRun(
                final_diagnosis=evidence, passed=False, answer_sufficient=False, retries=0,
                attempts=[CriticAttempt(attempt=1, diagnosis=evidence, critique=rejection)],
                metrics=Metrics(),
            )

    meter, planner, research, _ = build_advanced()
    run = asyncio.run(MultiAgentVersion(planner, research, RejectingCritic(), meter).run(
        question_text(questions("fixture")[0]),
    ))
    assert run.response.answer == REVIEW_FAILED
    assert run.response.sources == [] and run.response.confidence == 0
    assert [task.status for task in run.executions][-2:] == ["failed", "failed"]
    assert quality(run.response, {"answerable": False}) == 0
