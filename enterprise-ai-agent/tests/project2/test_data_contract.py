"""Wrong registered resource must fail before either Worker starts."""
from pathlib import Path
from fastapi.testclient import TestClient
from agents.project2.policy import TrustedContext
from api.project2_main import create_app
from tools.techqa_document_query import DatabaseWorker
from tests.project2.test_core import ROOT, original_sample


def test_manifest_mismatch():
    context=TrustedContext('contract-owner','local',frozenset({'full'}),frozenset({'document_count','rag_explain'}))
    app=create_app(credentials={'test':context},warmup=False)
    app.state.supervisor.database=DatabaseWorker(ROOT/'.rag_data/techqa_fixture.sqlite')
    result=TestClient(app).post('/v1/project2/analysis',headers={'Authorization':'Bearer test'},
                              json={'query':original_sample('P2-ENTITY-01')['query']}).json()
    assert result['status']=='failed'
    assert result['usage']['attempts']==0
    assert all(worker['error']['category']=='data_version_mismatch' for worker in result['workers'].values())
