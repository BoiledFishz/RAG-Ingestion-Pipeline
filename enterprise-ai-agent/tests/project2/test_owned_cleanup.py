"""Owned process cleanup may not depend on taskkill opening another process."""
import asyncio
import json
from pathlib import Path
import pytest
from agents.project2.rag_process import BoundedRAGProcess
ROOT=Path(__file__).resolve().parents[3]

def test_idle_cleanup_closes_stdin_before_force_and_does_not_use_taskkill(monkeypatch):
    events=[]
    class Pipe:
        def close(self):events.append('close')
    class Owned:
        stdin=Pipe();stdout=Pipe();pid=123
        def poll(self):return None if 'wait' not in events else 0
        def wait(self,timeout):events.append('wait');return 0
    environment=json.loads((ROOT/'evals/protocol_v0/baseline_v0.config.json').read_text(encoding='utf-8'))['environment']
    runtime=BoundedRAGProcess(environment);runtime.process=Owned();runtime.ready=True
    def forbidden(*args,**kwargs):raise AssertionError('taskkill must not be the normal idle cleanup path')
    monkeypatch.setattr('subprocess.run',forbidden)
    runtime.stop()
    assert events[:2]==['close','wait'] and runtime.process is None
