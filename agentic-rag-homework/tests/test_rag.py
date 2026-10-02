import asyncio

from evaluation.factory import build_rag


def test_clear_question_has_grounded_structured_answer() -> None:
    response = asyncio.run(
        build_rag().run("How are Streams environment variables set after upgrade to 4.1.1.2?")
    )
    assert response.sources
    assert "setproperty" in response.answer
    assert 0 < response.confidence <= 1
    assert all(source.quote for source in response.sources)


def test_ambiguous_question_asks_for_clarification() -> None:
    response = asyncio.run(build_rag().run("权限有问题"))
    assert "补充" in response.answer
    assert response.sources == []
    assert response.confidence == 0


def test_unknown_question_refuses_instead_of_hallucinating() -> None:
    response = asyncio.run(build_rag().run("What is the DynamoDB global table limit?"))
    assert response.sources == []
    assert response.confidence == 0
    assert "没有足够信息" in response.answer
