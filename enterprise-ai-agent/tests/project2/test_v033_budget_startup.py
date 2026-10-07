"""Fail-first contracts for the directly authorized budget/readiness change."""
import asyncio
import json
from pathlib import Path
import pytest
from agents.project2.budget import Budget,BudgetExceeded
ROOT=Path(__file__).resolve().parents[3]

def test_default_budget_is_90_seconds_with_unchanged_attempt_caps():
    b=Budget()
    assert 89 < b.remaining() <=90
    assert (b.max_attempts,b.max_llm_calls)==(19,6)
    for _ in range(19):b.reserve('db')
    with pytest.raises(BudgetExceeded,match='dependency_attempt_limit'):b.reserve('db')
    b=Budget()
    for _ in range(6):b.reserve('llm')
    with pytest.raises(BudgetExceeded,match='llm_attempt_limit'):b.reserve('llm')
    with pytest.raises(ValueError):Budget(seconds=90.001)

def test_runtime_policy_has_signed_floor_without_rewriting_old_policy():
    from agents.project2.execution_clock import load_policy
    assert load_policy(ROOT,'v0.3.3')['execution_limit_seconds']==90
    assert load_policy(ROOT,'v0.3.2')['execution_limit_seconds']==37.941018

def test_cold_runtime_never_initializes_inside_a_run_budget():
    from agents.project2.rag_process import BoundedRAGProcess
    env=json.loads((ROOT/'evals/protocol_v0/baseline_v0.config.json').read_text(encoding='utf-8'))['environment']
    runtime=BoundedRAGProcess(env);runtime.startup_required=True
    called=[]
    async def start():called.append(True);return {'type':'ready'}
    runtime.start=start
    query=json.loads((ROOT/'specs/project2/v0.3.3/task_preregistration.json').read_text(encoding='utf-8'))['samples'][0]['query']
    async def scenario():
        b=Budget()
        with pytest.raises(RuntimeError,match='worker_not_ready'):await runtime.run(query,b)
        assert not called and b.attempts==0
    asyncio.run(scenario())

def test_real_warmup_reads_only_official_corpus_and_leaves_requests_unstarted():
    from agents.project2.startup_warmup import warm_engine
    vectors=[];searches=[]
    class Encoder:
        def encode(self,texts):vectors.extend(texts);return [[1]]
    class Index:
        def search(self,v,k):searches.append((v,k));return ([[1]],[[0]])
    class Engine:encoder=Encoder();index=Index()
    result=warm_engine(Engine(),ROOT/'.rag_data/techqa_full.sqlite')
    assert result['completed'] and len(vectors)==1 and searches==[([[1]],1)]
    assert result['text_sha256'] and result['qa_fields_used']==[] and result['llm_calls']==0

def test_partial_worker_timeout_is_counted_in_smoke():
    from project2_v033_metrics import worker_flags
    r={'result':{'status':'partial','workers':{'rag':{'status':'timeout'},'database':{'status':'completed'}}}}
    flags=worker_flags(r)
    assert flags['any_worker_failed_or_timeout']==1
    assert flags['rag_failed_or_timeout']==1 and flags['database_failed_or_timeout']==0
    r['result']['workers']['rag']['status']='no_data'
    assert worker_flags(r)['any_worker_failed_or_timeout']==0
