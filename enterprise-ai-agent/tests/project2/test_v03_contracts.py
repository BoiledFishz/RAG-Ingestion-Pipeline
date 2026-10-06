from __future__ import annotations
import asyncio
import json
from pathlib import Path
from agents.project2.budget import Budget
from agents.project2.policy import TrustedContext
from agents.project2.supervisor import Supervisor
from models.project2 import AnalysisRequest
from tools.techqa_document_query import DatabaseWorker

ROOT=Path(__file__).resolve().parents[3]


def sample():
    rows=json.loads((ROOT/'specs/project2/v0.3/task_preregistration.json').read_text(encoding='utf-8'))['samples']
    item=next(x for x in rows if x['stratum']=='entity')
    return AnalysisRequest(query=item['query'])


def context():
    return TrustedContext('contract-owner','local',frozenset({'full'}),frozenset({'document_count','rag_explain'}))


class InvalidRAG:
    async def run(self,query,budget):
        return {'type':'result','data':{'trace':{'status':'answered','original_query':query},
                                      'response':{'answer':'','sources':[],'confidence':0}}}


def test_completed_cannot_be_inferred_from_empty_evidence():
    data=asyncio.run(Supervisor(DatabaseWorker(ROOT/'.rag_data/techqa_full.sqlite'),InvalidRAG()).run(sample(),context(),Budget()))
    assert data['workers']['rag']['status']=='failed'
    assert data['workers']['rag']['error']['category']=='invalid_evidence'


def test_default_response_contains_specified_trace_and_result_fields():
    data=asyncio.run(Supervisor(DatabaseWorker(ROOT/'.rag_data/techqa_full.sqlite'),InvalidRAG()).run(sample(),context(),Budget()))
    assert {'status','answer','evidence','data_results','limitations','worker_results','run_id','trace_id','usage'}<=set(data)
    assert data['trace_id']
    assert data['worker_results']==data['workers']
