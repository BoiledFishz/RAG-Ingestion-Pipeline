"""Real full-corpus counts while no RAG/vector/model object is constructed."""
import asyncio
import builtins
import json
from agents.project2.budget import Budget
from models.project2 import AnalysisRequest
from tools.techqa_document_query import DatabaseWorker
from tests.project2.test_core import ROOT, original_sample, owner


def test_real_db_without_rag_dependencies(monkeypatch):
    original=builtins.__import__
    def reject_heavy(name,*args,**kwargs):
        if name.startswith(('torch','faiss','models.providers','agents.rag_agent','agents.project2.rag_process')):
            raise RuntimeError('LLM/vector/RAG unavailable for independent DB test')
        return original(name,*args,**kwargs)
    monkeypatch.setattr(builtins,'__import__',reject_heavy)
    sample=original_sample('P2-ENTITY-01');budget=Budget()
    expected=json.loads((ROOT/'audit/project2-v1/preflight_report.json').read_text(encoding='utf-8'))['sample_measurements'][sample['sample_id']]
    result=asyncio.run(DatabaseWorker(ROOT/'.rag_data/techqa_full.sqlite').run(
        AnalysisRequest(query=sample['query']),owner(),budget,'independent-real-db'))
    assert [x['count'] for x in result.payload['groups']]==expected['counts']
    assert result.status=='completed' and budget.llm_calls==0 and set(budget.kinds)=={'db'}
