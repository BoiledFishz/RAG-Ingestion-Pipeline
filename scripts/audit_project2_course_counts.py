"""Fixed 50 query-side tasks: real Worker versus independent read-only oracle."""
from __future__ import annotations
import asyncio
import hashlib
import json
import logging
import sqlite3
import sys
import time
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'enterprise-ai-agent')]
LOGGER=logging.getLogger(__name__)


async def main():
    from agents.project2.budget import Budget,prepare_budget_configuration
    from agents.project2.policy import TrustedContext
    from tools.techqa_document_query import DatabaseWorker
    from models.project2 import AnalysisRequest
    prepare_budget_configuration()
    docs=ROOT/'specs/project2/v0.3.4'
    tasks=json.loads((docs/'task_preregistration.json').read_text(encoding='utf-8'))
    expected=json.loads((docs/'data_expectations.json').read_text(encoding='utf-8'))['sample_measurements']
    worker=DatabaseWorker(ROOT/'.rag_data/techqa_full.sqlite')
    owner=TrustedContext('course-owner','course',frozenset({'full'}),frozenset({'document_count','compare_document_counts'}))
    rows=[]
    with sqlite3.connect((ROOT/'.rag_data/techqa_full.sqlite').as_uri()+'?mode=ro',uri=True) as db:
        db.execute('PRAGMA query_only=ON')
        for task in tasks['samples']:
            source=expected[task['sample_id']]
            count=[];overlap=None
            def phrase(g):return ' AND '.join('"'+s.replace('"','""')+'"' for s in g)
            for group in source['predicates']:
                count.append(db.execute('SELECT COUNT(DISTINCT d.doc_id) FROM docs AS d JOIN search AS s ON s.rowid=d.rowid WHERE search MATCH ?',(phrase(group),)).fetchone()[0])
            if len(source['predicates'])==2:
                overlap=db.execute('SELECT COUNT(*) FROM (SELECT d.doc_id FROM docs AS d JOIN search AS s ON s.rowid=d.rowid WHERE search MATCH ? INTERSECT SELECT d.doc_id FROM docs AS d JOIN search AS s ON s.rowid=d.rowid WHERE search MATCH ?)',tuple(phrase(g) for g in source['predicates'])).fetchone()[0]
            preflight_equal=count==source['counts'] and overlap==source.get('intersection')
            request=AnalysisRequest(query=task['query'],analysis_operation=task['analysis_operation'],include_samples=False)
            started=time.perf_counter()
            result=await worker.run(request,owner,Budget(),task['query_sha256'][:32])
            payload=result.payload
            if source.get('error'):
                match=result.status=='failed' and result.error['category']=='clarification_required' and not payload['measurement_complete']
            else:
                match=([g['predicate'] for g in payload['groups']]==source['predicates']
                       and [g['count'] for g in payload['groups']]==count
                       and payload['intersection']==overlap and payload['measurement_complete'])
            rows.append({'sample_id':task['sample_id'],'query_sha256':task['query_sha256'],
                'independent_counts':count,'independent_intersection':overlap,'approved_expectation_matches_recount':preflight_equal,
                'worker_counts':[g['count'] for g in payload['groups']], 'worker_predicates':[g['predicate'] for g in payload['groups']],
                'worker_status':result.status,'worker_error':result.error,'passed':bool(match and preflight_equal),
                'elapsed_seconds':time.perf_counter()-started,'worker_llm_calls':result.usage['llm_calls']})
    report={'status':'passed' if all(r['passed'] for r in rows) else 'failed',
        'scope':'only tune registration; DB-only current-code verification, not held-out or RAG evaluation',
        'evidence_type':'真实运行','checks':rows,'numerator':sum(r['passed'] for r in rows),'denominator':len(rows),
        'new_heldout_calls':0,'new_model_calls':0,'llm_vector_rag_disabled':True,
        'spec_manifest_sha256':hashlib.sha256((docs/'version_manifest.json').read_bytes()).hexdigest(),
        'worker_sha256':hashlib.sha256((ROOT/'enterprise-ai-agent/tools/techqa_document_query.py').read_bytes()).hexdigest(),
        'historical_records_modified':False}
    target=ROOT/'audit/project2-course-completion-20261007/counts_v034.json'
    if target.exists():raise FileExistsError('Never overwrite completed audit')
    target.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    LOGGER.info('Independent COUNT gate %s: %s/%s',report['status'],report['numerator'],report['denominator'])
    return int(report['status']!='passed')


if __name__=='__main__':
    logging.basicConfig(level=logging.INFO)
    raise SystemExit(asyncio.run(main()))
