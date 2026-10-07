"""Dependency wrapper must not erase a real HTTP timeout or leave it uncancelled."""
import asyncio
import json
from pathlib import Path
import httpx
import pytest
from agents.project2.budget import Budget,prepare_budget_configuration
from agents.project2.rag_process import BoundedRAGProcess
ROOT=Path(__file__).resolve().parents[3]
def test_wrapped_real_http_timeout_is_recognized_without_classifying_other_errors():
    from agents.project2.rag_process import dependency_timeout
    error=RuntimeError('provider failed');error.__cause__=httpx.ReadTimeout('transport timeout')
    assert dependency_timeout(error)
    assert not dependency_timeout(RuntimeError('parse failed'))

def test_timeout_message_cancels_owned_child_and_propagates_timeout():
    prepare_budget_configuration()
    env=json.loads((ROOT/'evals/protocol_v0/baseline_v0.config.json').read_text(encoding='utf-8'))['environment']
    runtime=BoundedRAGProcess(env);runtime.startup_required=True;runtime.ready=True
    class Pipe:
        def write(self,text):pass
        def flush(self):pass
        def readline(self):return json.dumps({'type':'error','category':'DependencyUnavailable','dependency_timeout':True})+'\n'
    class Process:
        stdin=Pipe();stdout=Pipe()
        def poll(self):return None
    runtime.process=Process();cancelled=[]
    runtime.stop=lambda:cancelled.append(True)
    query=json.loads((ROOT/'specs/project2/v0.3.3/task_preregistration.json').read_text(encoding='utf-8'))['samples'][0]['query']
    async def run():
        with pytest.raises(TimeoutError):await runtime.run(query,Budget())
    asyncio.run(run())
    assert cancelled==[True]
