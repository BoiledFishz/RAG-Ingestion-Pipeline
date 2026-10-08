"""Runtime contracts use original official TechQA requests; no fake corpus."""
import asyncio
import json
from pathlib import Path
import pytest
from agents.project2.budget import Budget
from agents.project2.policy import TrustedContext

ROOT = Path(__file__).resolve().parents[3]


def request_body():
    from models.project2 import AnalysisRequest
    samples = json.loads((ROOT/'specs/project2/v0.3.1/task_preregistration.json').read_text(encoding='utf-8'))['samples']
    return AnalysisRequest(query=samples[0]['query'])


def owner(subject='runtime-owner'):
    return TrustedContext(subject, 'local', frozenset({'full'}), frozenset({'document_count', 'rag_explain'}))


def test_owner_isolation_and_invalid_states(tmp_path):
    from agents.project2.service_runtime import StateStore, RuntimeRejected
    store = StateStore(tmp_path, 'version')
    state = store.create(request_body(), owner(), Budget())
    assert store.load(state['run_id'], owner())['run_id']==state['run_id']
    with pytest.raises(RuntimeRejected, match='permission_denied'):
        store.load(state['run_id'], owner('other'))
    with pytest.raises(RuntimeRejected, match='unknown_run'):
        store.load('0'*32, owner())
    state['lifecycle']='made_up';store.write(state)
    with pytest.raises(RuntimeRejected, match='illegal_state'):
        store.load(state['run_id'], owner())


def test_duplicate_resume_and_unknown_attempt(tmp_path):
    from agents.project2.service_runtime import StateStore, RuntimeRejected, bind_budget
    store = StateStore(tmp_path, 'version')
    budget = Budget();state = store.create(request_body(), owner(), budget)
    bind_budget(budget, store, state)
    budget.reserve('llm');budget.reserve('db')
    saved = store.load(state['run_id'], owner())
    restored = Budget();bind_budget(restored, store, saved, restore=True)
    assert restored.attempts==2 and restored.llm_calls==1
    assert restored.absolute_deadline==budget.absolute_deadline
    with store.lease(state['run_id']):
        with pytest.raises(RuntimeRejected, match='run_busy'):
            with store.lease(state['run_id']):pass


def test_invalid_expired_resume(tmp_path):
    from agents.project2.service_runtime import StateStore, RuntimeRejected
    store = StateStore(tmp_path, 'version');state = store.create(request_body(), owner(), Budget())
    state['expires_at']=0;store.write(state)
    with pytest.raises(RuntimeRejected, match='state_expired'):store.load(state['run_id'], owner())
    state['expires_at']=10**12;state['version']='changed';store.write(state)
    with pytest.raises(RuntimeRejected, match='version_mismatch'):store.load(state['run_id'], owner())


def test_runtime_state_never_contains_credentials_or_prompts(tmp_path):
    from agents.project2.service_runtime import StateStore, bind_budget
    store = StateStore(tmp_path, 'version');budget = Budget()
    state = store.create(request_body(), owner(), budget);bind_budget(budget, store, state)
    budget.reserve('db')
    text = (tmp_path/(state['run_id']+'.json')).read_text(encoding='utf-8')
    assert 'authorization' not in text and 'Bearer' not in text and 'prompt' not in text
    events = [json.loads(x) for x in (tmp_path/'traces'/(state['run_id']+'.jsonl')).read_text(encoding='utf-8').splitlines()]
    assert any(x['stage']=='dependency' and x['kind']=='db' and x['parent_span_id'] for x in events)


def test_state_ttl_cleanup_and_trace_request_identity(tmp_path):
    from agents.project2.service_runtime import StateStore
    store=StateStore(tmp_path,'version');state=store.create(request_body(),owner(),Budget())
    state['expires_at']=0;store.write(state)
    StateStore(tmp_path,'version')
    assert not (tmp_path/(state['run_id']+'.json')).exists()
    events=[json.loads(x) for x in (tmp_path/'traces'/(state['run_id']+'.jsonl')).read_text(encoding='utf-8').splitlines()]
    assert all(event.get('request_id') for event in events)
def test_atomic_checkpoint_retries_transient_sharing_violation_but_is_bounded(tmp_path, monkeypatch):
    from agents.project2.service_runtime import StateStore
    import os
    store = StateStore(tmp_path, 'version')
    state = store.create(request_body(), owner(), Budget())
    original = os.replace
    attempts = []
    def transient(source, target):
        attempts.append(1)
        if len(attempts) == 1:
            raise PermissionError('simulated Windows read sharing violation')
        return original(source, target)
    monkeypatch.setattr(os, 'replace', transient)
    store.write(state)
    assert len(attempts) == 2
    def permanent(source, target):
        attempts.append(1)
        raise PermissionError('permanent access denial')
    monkeypatch.setattr(os, 'replace', permanent)
    attempts.clear()
    with pytest.raises(PermissionError):
        store.write(state)
    assert len(attempts) == 4
    assert not list(tmp_path.glob('*.tmp'))


def test_initial_result_matches_persisted_result_and_terminal_resume(tmp_path, monkeypatch):
    """Replay an actual TechQA result; contract evidence only, no fake corpus."""
    import copy
    from types import SimpleNamespace
    from agents.project2.service_runtime import RuntimeCoordinator, StateStore
    from agents.project2.supervisor import Supervisor

    recorded = json.loads((ROOT / 'audit/project2-course-completion-20261007/'
                           'container_gate_round2/combined_response.json').read_text(encoding='utf-8'))
    async def recorded_run(self, request, context, budget):
        return copy.deepcopy(recorded)
    monkeypatch.setattr(Supervisor, 'run', recorded_run)
    store = StateStore(tmp_path, 'contract-replay')
    database = SimpleNamespace(path=ROOT / '.rag_data/techqa_full.sqlite')
    coordinator = RuntimeCoordinator(Supervisor(database, SimpleNamespace()), store)
    initial = asyncio.run(coordinator.analyze(request_body(), owner(), Budget()))
    stored = store.load(initial['run_id'], owner())['result']
    resumed = asyncio.run(coordinator.resume(initial['run_id'], owner(), Budget()))
    assert initial == stored == resumed
    assert initial['answer'] == recorded['answer']
    assert initial['data_results'] == recorded['data_results']
    assert initial['evidence'] == recorded['evidence']
