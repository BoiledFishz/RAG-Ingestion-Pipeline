"""Passive measurement must not alter the retrieved candidates."""
import asyncio
import json
from pathlib import Path
from types import SimpleNamespace
from agents.project2.observability import observe_pipeline

ROOT=Path(__file__).resolve().parents[3]

def test_pipeline_stage_is_identical_to_frozen_v0_evaluator():
    row=json.loads((ROOT/'evals/protocol_v0/runs/baseline-v0-quick/tune/runs.json').read_text(encoding='utf-8'))[0]
    ids=row['native']['pipeline']['candidate_ids']
    outcome=SimpleNamespace(results=[SimpleNamespace(chunk_id=x) for x in ids],diagnostics=SimpleNamespace(reranker_fallback=False))
    async def retrieve(query):return outcome
    pipeline=SimpleNamespace(retrieve=retrieve);observed={}
    observe_pipeline(pipeline,observed)
    actual=asyncio.run(pipeline.retrieve(row['native']['run']['trace']['original_query']))
    assert actual is outcome
    assert observed=={'candidate_ids':ids,'reranker_fallback':False,'stage':'retrieval_pipeline_before_parent_expansion'}
