"""Recovery accounting contracts, using registered original TechQA inputs."""
import json
import time
from pathlib import Path
import pytest
from agents.project2.budget import Budget, BudgetExceeded
from agents.project2.policy import TrustedContext
from models.project2 import AnalysisRequest

ROOT=Path(__file__).resolve().parents[3]
def request():
    return AnalysisRequest(query=json.loads((ROOT/'specs/project2/v0.3.2/task_preregistration.json').read_text(encoding='utf-8'))['samples'][0]['query'])
def owner():return TrustedContext('owner','local',frozenset({'full'}),frozenset({'document_count','rag_explain'}))
def store_at(path):
    from agents.project2.service_runtime import StateStore
    from agents.project2.execution_clock import load_policy
    return StateStore(path,'v032',execution_policy=load_policy(ROOT))

def test_stopped_time_excluded_but_active_time_and_attempts_accumulate(tmp_path):
    from agents.project2.service_runtime import bind_budget
    store=store_at(tmp_path);budget=Budget();state=store.create(request(),owner(),budget)
    bind_budget(budget,store,state);budget.reserve('llm');time.sleep(.04)
    budget.execution_ledger.finish()
    saved=store.load(state['run_id'],owner());consumed=saved['budget']['execution']['consumed_seconds']
    assert consumed>=.04 and saved['budget']['execution']['segments'][0]['closed']
    time.sleep(.2)  # Downtime has real duration and must not consume the limit.
    restored=Budget();bind_budget(restored,store,saved,restore=True)
    assert restored.attempts==1 and restored.llm_calls==1
    assert restored.absolute_deadline>budget.absolute_deadline+.1
    assert 37.941018-consumed-.08 < restored.remaining() <=37.941018-consumed
    restored.reserve('db');time.sleep(.03);restored.execution_ledger.finish()
    final=store.load(state['run_id'],owner())['budget']
    assert final['attempts']==2 and final['llm_calls']==1
    assert final['execution']['consumed_seconds']>=consumed+.03
    assert len(final['execution']['segments'])==2

def test_lifetime_and_cumulative_expiry_never_reset_or_start_dependency(tmp_path):
    from agents.project2.service_runtime import bind_budget
    store=store_at(tmp_path);budget=Budget();state=store.create(request(),owner(),budget)
    bind_budget(budget,store,state);budget.reserve('db');budget.execution_ledger.finish()
    state=store.load(state['run_id'],owner());state['created_at']=time.time()-901;store.write(state)
    resumed=Budget()
    with pytest.raises(BudgetExceeded,match='run_lifetime_exhausted'):bind_budget(resumed,store,state,restore=True)
    assert resumed.attempts==1
    state['created_at']=time.time();execution=state['budget']['execution']
    execution['segments'][0]['consumed_seconds']=execution['limit_seconds']+.01
    execution['consumed_seconds']=execution['limit_seconds']+.01
    store.write(state)
    with pytest.raises(BudgetExceeded,match='cumulative_execution_exhausted'):bind_budget(Budget(),store,state,restore=True)
    assert store.load(state['run_id'],owner())['budget']['attempts']==1

def test_hard_stop_tail_is_charged_and_nonfinite_ledger_is_rejected(tmp_path):
    from agents.project2.service_runtime import bind_budget,RuntimeRejected
    store=store_at(tmp_path);budget=Budget();state=store.create(request(),owner(),budget)
    bind_budget(budget,store,state);budget.execution_ledger.finish()
    state=store.load(state['run_id'],owner());before=state['budget']['execution']['consumed_seconds']
    state['budget']['execution']['segments'][0]['closed']=False;store.write(state)
    restored=Budget();bind_budget(restored,store,state,restore=True);restored.execution_ledger.finish()
    assert state['budget']['execution']['consumed_seconds']>=before+.25
    state['budget']['execution']['consumed_seconds']=float('nan');store.write(state)
    with pytest.raises(RuntimeRejected,match='illegal_state'):store.load(state['run_id'],owner())

def test_heartbeat_persists_pending_model_time_without_new_attempt(tmp_path):
    from agents.project2.service_runtime import bind_budget
    store=store_at(tmp_path);budget=Budget();state=store.create(request(),owner(),budget)
    bind_budget(budget,store,state);budget.reserve('llm');time.sleep(.32)
    saved=store.load(state['run_id'],owner())['budget']
    assert saved['execution']['consumed_seconds']>=.25 and saved['llm_calls']==1
    budget.execution_ledger.finish()
