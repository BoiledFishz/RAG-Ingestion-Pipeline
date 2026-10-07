"""Local subprocess fixture, with one registered real SQLite schema fault.

Fault switch exists in this gate fixture only, not the public service contract.
No corpus is changed and no fabricated Worker response is used.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import logging
import sqlite3
import sys
import time
from contextlib import asynccontextmanager
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
PROCESS_ENTRY_WALL=time.time()
sys.path.insert(0, str(ROOT/'enterprise-ai-agent'))


def main() -> None:
    logging.basicConfig(level=logging.INFO,format='%(asctime)s %(levelname)s %(message)s')
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--port', required=True, type=int)
    ap.add_argument('--state-directory', required=True, type=Path)
    ap.add_argument('--fault-database-schema', action='store_true')
    args=ap.parse_args()
    import uvicorn
    from api.project2_runtime_main import create_app
    from agents.project2.policy import TrustedContext
    from tools.techqa_document_query import DatabaseWorker
    owner=TrustedContext('gate-owner','local',frozenset({'full'}),frozenset({'document_count','compare_document_counts','rag_explain'}))
    other=TrustedContext('gate-other','local',owner.allowed_corpus_scopes,owner.allowed_operations)
    revoked=TrustedContext('gate-owner','local',frozenset({'full'}),frozenset({'document_count'}))
    app=create_app(credentials={'gate-owner-token':owner,'gate-other-token':other,'gate-revoked-token':revoked}, state_directory=args.state_directory)
    if args.fault_database_schema:
        class FaultDatabase(DatabaseWorker):
            def _execute(self, request, groups, budget, result):
                budget.reserve('db')
                with sqlite3.connect(self.path.as_uri()+'?mode=ro', uri=True, timeout=budget.remaining(12)) as db:
                    db.execute('SELECT COUNT(*) FROM __project2_gate_missing_table')
        app.state.service_runtime.database=FaultDatabase(ROOT/'.rag_data/techqa_full.sqlite')
    original=app.state.rag_runtime.run
    async def hashed_native(query, budget):
        message=await original(query,budget)
        if message.get('type')=='result':
            body=message['data']['response']['answer']
            logging.getLogger(__name__).info('NATIVE_BODY run=%s sha256=%s', budget.run_id, hashlib.sha256(body.encode()).hexdigest())
        return message
    app.state.rag_runtime.run=hashed_native
    original_lifespan=app.router.lifespan_context
    @asynccontextmanager
    async def measured_lifespan(application):
        async with original_lifespan(application):
            timings={'process_entry_wall_time':PROCESS_ENTRY_WALL,'ready_wall_time':time.time(),
                     'api_process_initialization_seconds':time.time()-PROCESS_ENTRY_WALL,
                     'rag_startup':application.state.rag_runtime.startup_observation,
                     'server_pid':__import__('os').getpid()}
            (args.state_directory.parent/('startup_'+str(args.port)+'.json')).write_text(json.dumps(timings,indent=2)+'\n',encoding='utf-8')
            yield
    app.router.lifespan_context=measured_lifespan
    uvicorn.run(app, host='127.0.0.1', port=args.port, access_log=True)


if __name__=='__main__':main()
