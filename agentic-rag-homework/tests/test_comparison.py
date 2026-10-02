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
