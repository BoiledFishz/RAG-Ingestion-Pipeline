"""Frozen hard caps; injecting failures cannot replenish attempts."""
import asyncio
import pytest
from agents.project2.budget import Budget, BudgetExceeded, read_frozen_limits
from agents.project2.policy import TrustedContext
from agents.project2.supervisor import Supervisor
from models.project2 import AnalysisRequest
from tools.techqa_document_query import DatabaseWorker
from tests.project2.test_core import ROOT, original_sample, owner


def test_api_call_caps():
    limits=read_frozen_limits()
    budget=Budget();started=[]
    for number in range(limits['attempts']): budget.reserve('db');started.append(number)
    with pytest.raises(BudgetExceeded): budget.reserve('db');started.append(limits['attempts'])
    assert len(started)==limits['attempts']
    budget=Budget();started=[]
    for number in range(limits['llm_calls']): budget.reserve('llm');started.append(number)
    with pytest.raises(BudgetExceeded): budget.reserve('llm');started.append(limits['llm_calls'])
    assert len(started)==limits['llm_calls']


def test_deadline_without_results():
    budget=Budget(seconds=.001)
    async def exercise():
        await asyncio.sleep(.01)
        with pytest.raises(BudgetExceeded):budget.reserve('db')
    asyncio.run(exercise())
    assert budget.attempts==0


def test_nested_attempts_and_cancellation():
    budget=Budget();budget.reserve('llm');budget.reserve('db')
    budget.cancel()
    with pytest.raises(BudgetExceeded):budget.reserve('llm')
    assert budget.snapshot()['attempts']==2 and budget.snapshot()['llm_calls']==1
    assert budget.snapshot()['estimated_tokens'] is None


def test_direct_worker_does_not_start_n_plus_one():
    budget=Budget()
    for _ in range(budget.max_attempts):budget.reserve('db')
    sample=original_sample('P2-ENTITY-01')
    result=asyncio.run(DatabaseWorker(ROOT/'.rag_data/techqa_full.sqlite').run(
        AnalysisRequest(query=sample['query']),owner(),budget,'hard-cap-contract'))
    assert result.status=='timeout' and budget.attempts==budget.max_attempts
    assert all(x['count'] is None for x in result.payload['groups'])

@pytest.mark.parametrize('kind',['db','llm'])
def test_default_api_stops_before_n_plus_one(kind):
    from api.project2_main import create_app
    from fastapi.testclient import TestClient
    limits=read_frozen_limits();started=[]
    class ConsumeBudget:
        async def run(self,query,budget):
            while True:
                budget.reserve(kind)
                started.append(kind)
    app=create_app(credentials={'cap-contract':owner()},warmup=False)
    app.state.supervisor.rag_process=ConsumeBudget()
    data=TestClient(app).post('/v1/project2/analysis',headers={'Authorization':'Bearer cap-contract'},
         json={'query':original_sample('P2-ENTITY-01')['query']}).json()
    assert data['workers']['database']['status']=='completed'
    assert data['workers']['rag']['status']=='timeout' and data['status']=='partial'
    usage=data['usage']
    if kind=='llm':
        assert len(started)==usage['llm_calls']==limits['llm_calls']
    else:
        db_attempts=data['workers']['database']['usage']['attempts']
        assert len(started)+db_attempts==usage['attempts']==limits['attempts']
