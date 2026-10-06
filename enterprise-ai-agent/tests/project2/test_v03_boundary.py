import asyncio
import json
from pathlib import Path
from fastapi.testclient import TestClient
from agents.project2.budget import Budget
from agents.project2.policy import TrustedContext
from api import project2_main

ROOT=Path(__file__).resolve().parents[3]


def original_query():
    data=json.loads((ROOT/'specs/project2/v0.3/task_preregistration.json').read_text(encoding='utf-8'))
    return next(x['query'] for x in data['samples'] if x['stratum']=='entity')


def test_whole_http_deadline_cancels_unfinished_dispatch(monkeypatch):
    monkeypatch.setattr(project2_main,'Budget',lambda:Budget(seconds=.05))
    owner=TrustedContext('timeout-owner','local',frozenset({'full'}),frozenset({'document_count','rag_explain'}))
    app=project2_main.create_app(credentials={'local-token':owner},warmup=False)
    cancelled=[]
    async def delayed_dispatch(*args):
        try:
            await asyncio.sleep(.5)
            return {}
        except asyncio.CancelledError:
            cancelled.append(True)
            raise
    monkeypatch.setattr(app.state.supervisor,'run',delayed_dispatch)
    response=TestClient(app).post('/v1/project2/analysis',headers={'Authorization':'Bearer local-token'},json={'query':original_query()})
    data=response.json()
    assert data['status']=='timeout'
    assert data['usage']['attempts']==0
    assert cancelled
    assert all(x['status']=='timeout' for x in data['workers'].values())
