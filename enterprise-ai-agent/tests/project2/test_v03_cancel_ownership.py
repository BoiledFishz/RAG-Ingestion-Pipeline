import asyncio
import json
from pathlib import Path
import pytest
from agents.project2.budget import Budget
from agents.project2.rag_process import BoundedRAGProcess

ROOT=Path(__file__).resolve().parents[3]


def test_queued_request_timeout_does_not_terminate_another_owner():
    environment=json.loads((ROOT/'evals/protocol_v0/baseline_v0.config.json').read_text(encoding='utf-8'))['environment']
    runtime=BoundedRAGProcess(environment)
    stopped=[]
    runtime.stop=lambda:stopped.append(True)
    query=json.loads((ROOT/'specs/project2/v0.3/task_preregistration.json').read_text(encoding='utf-8'))['samples'][0]['query']
    async def exercise():
        await runtime.lock.acquire()
        try:
            with pytest.raises(TimeoutError):
                await runtime.run(query,Budget(seconds=.02))
        finally:
            runtime.lock.release()
    asyncio.run(exercise())
    assert not stopped
