"""Lineage contract from immutable real RAG records, no generated test corpus."""
import asyncio
import json
from pathlib import Path
from agents.project2.budget import Budget
from agents.project2.policy import TrustedContext
from agents.project2.supervisor import Supervisor
from models.project2 import AnalysisRequest
from tools.techqa_document_query import DatabaseWorker

ROOT=Path(__file__).resolve().parents[3]


def test_real_source_positions_and_compression_are_exposed_without_changing_answer():
    raw=ROOT/'evals/project2-v1/calibration_v03/requests.jsonl'
    record=next(json.loads(line) for line in raw.read_text(encoding='utf-8').splitlines()
                if json.loads(line)['path']=='rag_only' and
                json.loads(line)['result'].get('data',{}).get('trace',{}).get('status')=='answered')
    message=record['result']
    class ReplayRAG:
        async def run(self, query, budget):
            assert query==message['data']['trace']['original_query']
            return message
    context=TrustedContext('contract-owner','local',frozenset({'full'}),frozenset({'document_count','rag_explain'}))
    result=asyncio.run(Supervisor(DatabaseWorker(ROOT/'.rag_data/techqa_full.sqlite'),ReplayRAG()).run(
        AnalysisRequest(query=message['data']['trace']['original_query']),context,Budget()))
    lineage=result['workers']['rag']['payload']['source_lineage']
    assert lineage and all(x['candidate_rank']>=1 and x['start_char'] is not None and x['end_char']>x['start_char'] for x in lineage)
    assert result['answer']==message['data']['response']['answer']
    assert result['workers']['rag']['payload']['original_query']==message['data']['trace']['original_query']
