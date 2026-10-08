"""Durable, owner-scoped service checkpoints; existing Supervisor is reused.

Metadata uses atomic local files, not a new SQL dependency/cache. Every actual
DB/model attempt still reserves the original frozen Budget before it starts.
Checkpoint I/O consumes the same wall-clock deadline. No prompt/credential is
stored. File leases survive multiple server processes and release on exit.
"""
from __future__ import annotations
import asyncio
import copy
import hashlib
import json
import logging
import os
import re
import time
from contextlib import contextmanager
from pathlib import Path
from threading import RLock
from uuid import uuid4
from typing import Iterator, Any

from agents.project2.budget import Budget, BudgetExceeded
from agents.project2.policy import TrustedContext
from agents.project2.supervisor import Supervisor
from models.project2 import AnalysisRequest, WorkerResult
from tools.techqa_document_query import DatabaseWorker

LOGGER = logging.getLogger(__name__)
STATES = {'completed', 'partial', 'no_data', 'permission_denied', 'timeout', 'failed'}


class RuntimeRejected(ValueError):
    pass


class StateStore:
    def __init__(self, directory: Path, version: str, *, execution_policy: dict | None=None) -> None:
        self.directory = directory.resolve();self.version = version;self.lock = RLock()
        self.directory.mkdir(parents=True, exist_ok=True)
        self.execution_policy=execution_policy
        (self.directory/'traces').mkdir(exist_ok=True)
        self.request_ids: dict[str,str]={}
        self.active_nodes: dict[str,tuple[str,str]]={}
        self.cleanup()

    def cleanup(self) -> None:
        now=time.time()
        for path in self.directory.glob('*.json'):
            if not re.fullmatch(r'[0-9a-f]{32}',path.stem) or path.is_symlink():continue
            try:expired=json.loads(path.read_text(encoding='utf-8'))['expires_at']<=now
            except (ValueError,KeyError):continue
            if expired:path.unlink()  # Only this Runtime's own nonrecursive TTL file.
        for path in (self.directory/'traces').glob('*.jsonl'):
            if not re.fullmatch(r'[0-9a-f]{32}',path.stem) or path.is_symlink():continue
            try:events=[json.loads(x) for x in path.read_text(encoding='utf-8').splitlines()]
            except ValueError:continue
            if events and max(x['timestamp'] for x in events)<=now-7*86400:path.unlink()

    def path(self, run_id: str) -> Path:
        if not re.fullmatch(r'[0-9a-f]{32}', run_id):raise RuntimeRejected('unknown_run')
        path=self.directory/(run_id+'.json')
        if path.resolve().parent!=self.directory:raise RuntimeRejected('illegal_state')
        return path

    def create(self, request: AnalysisRequest, context: TrustedContext, budget: Budget) -> dict:
        if not context or not (context.permits(request.analysis_operation) or context.permits('rag_explain')):
            raise RuntimeRejected('permission_denied')
        budget.remaining();now = time.time();body = request.model_dump(mode='json')
        state = {'run_id': uuid4().hex, 'request_id': uuid4().hex, 'owner': context.subject_id, 'tenant': context.tenant_id,
                 'policy_version': 'trusted-full-readonly-v1', 'version': self.version,
                 'request': body, 'request_sha256': hashlib.sha256(json.dumps(body, sort_keys=True).encode()).hexdigest(),
                 'created_at': now, 'expires_at': now+86400, 'lifecycle': 'created',
                 'budget': budget.snapshot(), 'nodes': {}, 'result': None}
        self.request_ids[state['run_id']]=state['request_id']
        self.write(state);self.trace(state['run_id'], 'request', 'created', parent=None)
        budget.remaining();return state

    def write(self, state: dict) -> None:
        path = self.path(state['run_id']);temporary = path.with_name(path.name+'.'+uuid4().hex+'.tmp')
        with self.lock:
            payload = json.dumps(state, ensure_ascii=False, separators=(',', ':')).encode()
            if len(payload) > 2_000_000:raise RuntimeRejected('checkpoint_size_limit')
            try:
                with temporary.open('xb') as handle:
                    handle.write(payload);handle.flush();os.fsync(handle.fileno())
                # Windows readers briefly hold handles without delete sharing.
                # At most 150 ms of bounded metadata retry, inside the original
                # request deadline; a persistent denial remains an error.
                for attempt in range(4):
                    try:
                        os.replace(temporary, path)
                        break
                    except PermissionError:
                        if attempt == 3:raise
                        LOGGER.warning('Checkpoint sharing violation run=%s retry=%s',state['run_id'],attempt+1)
                        time.sleep(.05)
            finally:
                if temporary.exists():temporary.unlink()

    def load(self, run_id: str, context: TrustedContext) -> dict:
        if not context or not context.subject_id or 'full' not in context.allowed_corpus_scopes:
            raise RuntimeRejected('permission_denied')
        path = self.path(run_id)
        if not path.is_file():raise RuntimeRejected('unknown_run')
        try:
            state = json.loads(path.read_text(encoding='utf-8'))
            if state['owner']!=context.subject_id or state['tenant']!=context.tenant_id:
                raise RuntimeRejected('permission_denied')
            request = AnalysisRequest.model_validate(state['request'])
            # Old results cannot be returned after any task permission is revoked.
            needed = state.get('authorized_operations', [request.analysis_operation, 'rag_explain'])
            if not all(context.permits(operation) for operation in needed):raise RuntimeRejected('permission_denied')
            if state['lifecycle'] not in {'created', 'running', 'interrupted', 'terminal'} or state['run_id']!=run_id:
                raise RuntimeRejected('illegal_state')
            if state['version']!=self.version or state['policy_version']!='trusted-full-readonly-v1':raise RuntimeRejected('version_mismatch')
            if state['expires_at']<=time.time():raise RuntimeRejected('state_expired')
            if hashlib.sha256(json.dumps(state['request'], sort_keys=True).encode()).hexdigest()!=state['request_sha256']:
                raise RuntimeRejected('illegal_state')
            for node in state['nodes'].values():WorkerResult.model_validate(node)
            if state.get('result') and state['result']['status'] not in STATES:raise RuntimeRejected('illegal_state')
            usage = state['budget']
            if type(usage['attempts']) is not int or type(usage['llm_calls']) is not int or not 0<=usage['llm_calls']<=usage['attempts']:
                raise RuntimeRejected('illegal_state')
            kinds=usage['attempts_by_kind']
            if any(type(x) is not int or x<0 for x in kinds.values()) or sum(kinds.values())!=usage['attempts'] or kinds.get('llm',0)!=usage['llm_calls']:
                raise RuntimeRejected('illegal_state')
            if self.execution_policy and 'execution' in usage:
                from agents.project2.execution_clock import validate_execution
                validate_execution(usage['execution'],self.execution_policy)
            elif self.execution_policy and state['lifecycle']!='created':
                raise RuntimeRejected('illegal_state')
            return state
        except RuntimeRejected:raise
        except Exception as error:raise RuntimeRejected('illegal_state') from error

    @contextmanager
    def lease(self, run_id: str) -> Iterator[None]:
        path = self.path(run_id).with_suffix('.lease')
        with path.open('a+b') as handle:
            try:
                handle.seek(0)
                if not handle.read(1):handle.write(b'0');handle.flush()
                handle.seek(0)
                if os.name=='nt':
                    import msvcrt
                    msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
                else:
                    import fcntl
                    fcntl.flock(handle, fcntl.LOCK_EX|fcntl.LOCK_NB)
            except OSError as error:raise RuntimeRejected('run_busy') from error
            try:yield
            finally:
                handle.seek(0)
                if os.name=='nt':msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
                else:fcntl.flock(handle, fcntl.LOCK_UN)

    def trace(self, run_id: str, stage: str, status: str, *, parent='request', **metadata) -> None:
        allowed = {'kind', 'attempts', 'llm_calls', 'error_category', 'elapsed_seconds', 'skipped', 'worker'}
        if set(metadata)-allowed:raise ValueError('Unregistered trace fields')
        span_id=run_id if not parent else uuid4().hex
        parent_span=self.active_nodes.get(run_id,(None,run_id))[1] if stage=='dependency' else run_id
        if stage in {'database','rag'}:
            if status=='started':self.active_nodes[run_id]=(stage,span_id)
            elif self.active_nodes.get(run_id,(None,None))[0]==stage:
                span_id=self.active_nodes.pop(run_id)[1]
        event = {'run_id': run_id, 'trace_id': run_id, 'request_id': self.request_ids.get(run_id,run_id), 'span_id': span_id,
                 'parent_span_id': parent_span if parent else None, 'stage': stage,
                 'status': status, 'timestamp': time.time(), **metadata}
        with self.lock, (self.directory/'traces'/(run_id+'.jsonl')).open('a', encoding='utf-8') as handle:
            handle.write(json.dumps(event)+'\n');handle.flush();os.fsync(handle.fileno())

    def read_trace(self, run_id: str, context: TrustedContext) -> list[dict]:
        self.load(run_id, context)
        path = self.directory/'traces'/(run_id+'.jsonl')
        return [event for line in path.read_text(encoding='utf-8').splitlines()
                if (event:=json.loads(line))['timestamp']>time.time()-7*86400]


def bind_budget(budget: Budget, store: StateStore, state: dict, *, restore=False) -> None:
    if restore:
        saved = state['budget']
        if saved['attempts']>budget.max_attempts or saved['llm_calls']>budget.max_llm_calls:
            raise RuntimeRejected('illegal_state')
        # Original absolute deadline; neither process startup nor retries reset it.
        if store.execution_policy is None:  # Historical v031 structural contracts only.
            budget.absolute_deadline = saved['absolute_deadline']
            budget.deadline = time.monotonic()+saved['absolute_deadline']-time.time()
        budget.attempts = saved['attempts'];budget.llm_calls = saved['llm_calls']
        budget.kinds.update(saved['attempts_by_kind'])
        if state['nodes'].get('database'):
            budget.database_result=WorkerResult.model_validate(state['nodes']['database'])
    if store.execution_policy:
        from agents.project2.execution_clock import ExecutionLedger
        try:ExecutionLedger(budget,store,state,restore=restore)
        except (ValueError,KeyError,TypeError) as error:raise RuntimeRejected('illegal_state') from error
    reserve = budget.reserve

    def durable_reserve(kind: str) -> None:
        with budget.lock:
            reserve(kind)  # Raises before any N+1/L+1 dependency can start.
            state['budget'] = budget.snapshot();store.write(state)
            store.trace(state['run_id'], 'dependency', 'reserved', kind=kind,
                        attempts=budget.attempts, llm_calls=budget.llm_calls)
            budget.remaining()
    budget.reserve = durable_reserve


class CheckpointDatabase:
    def __init__(self, database: DatabaseWorker, store: StateStore, state: dict) -> None:
        self.database = database;self.path = database.path;self.store = store;self.state = state

    async def run(self, request: AnalysisRequest, context: TrustedContext, budget: Budget, run_id: str) -> WorkerResult:
        saved = self.state['nodes'].get('database')
        if saved and saved['status'] in {'completed', 'no_data'}:
            restored = WorkerResult.model_validate(saved);restored.run_id = run_id
            self.store.trace(self.state['run_id'], 'database', restored.status, skipped=True)
            return restored
        self.store.trace(self.state['run_id'], 'database', 'started')
        result = await self.database.run(request, context, budget, run_id)
        validated = WorkerResult.model_validate(result.model_dump(mode='json'))
        self.state['nodes']['database'] = {**validated.model_dump(mode='json'), 'run_id': self.state['run_id']}
        self.state['budget'] = budget.snapshot();self.store.write(self.state)
        self.store.trace(self.state['run_id'], 'database', validated.status, skipped=False,
                         error_category=(validated.error or {}).get('category'))
        return validated


class RuntimeCoordinator:
    def __init__(self, supervisor: Supervisor, store: StateStore) -> None:
        self.original = supervisor.run;self.database = supervisor.database
        self.rag_process = supervisor.rag_process;self.registered_path = supervisor.registered_database_path
        self.store = store

    async def analyze(self, request: AnalysisRequest, context: TrustedContext, budget: Budget) -> dict:
        if not context or not (context.permits(request.analysis_operation) or context.permits('rag_explain')):
            return await self.original(request, context, budget)
        state = self.store.create(request, context, budget)
        state['authorized_operations'] = [op for op in (request.analysis_operation, 'rag_explain') if context.permits(op)]
        self.store.write(state)
        with self.store.lease(state['run_id']):
            return await self.execute(state, context, budget, resume=False)

    async def resume(self, run_id: str, context: TrustedContext, budget: Budget) -> dict:
        self.store.load(run_id, context)  # Reauthorize before even acquiring a lease.
        with self.store.lease(run_id):
            state = self.store.load(run_id, context)
            self.store.request_ids[run_id]=uuid4().hex
            bind_budget(budget, self.store, state, restore=True)
            budget.run_id = run_id
            if state['lifecycle']=='terminal' and state.get('result'):
                self.store.trace(run_id, 'resume', state['result']['status'], skipped=True)
                return state['result']
            budget.remaining()
            return await self.execute(state, context, budget, resume=True, already_bound=True)

    async def execute(self, state: dict, context: TrustedContext, budget: Budget, *, resume: bool, already_bound=False) -> dict:
        if not already_bound:bind_budget(budget, self.store, state)
        state['lifecycle']='running';self.store.write(state)
        self.store.trace(state['run_id'], 'resume' if resume else 'supervisor', 'started')
        proxy = CheckpointDatabase(self.database, self.store, state)
        class TracedRAG:
            async def run(inner, query: str, active_budget: Budget) -> dict:
                self.store.trace(state['run_id'],'rag','started')
                return await self.rag_process.run(query,active_budget)
        supervisor = Supervisor(proxy, TracedRAG(), registered_database_path=self.registered_path)
        started = time.monotonic()
        try:
            async with asyncio.timeout(budget.remaining()):
                result = await supervisor.run(AnalysisRequest.model_validate(state['request']), context, budget)
            result['run_id']=state['run_id'];result['trace_id']=state['run_id'];budget.run_id=state['run_id']
            result['request_id']=self.store.request_ids.get(state['run_id'],state['request_id'])
            for worker in result['workers'].values():
                worker['run_id']=state['run_id'];WorkerResult.model_validate(worker)
            result['worker_results']=result['workers']
            # Original answer and citations untouched; retain validated results.
            stored=copy.deepcopy(result)
            for worker in stored['workers'].values():
                payload=worker.get('payload',{})
                if 'trace' in payload:
                    payload['trace']={key:value for key,value in payload['trace'].items()
                        if key in {'original_query','rewritten_query','rewrite_fallback','tool_called','candidate_ids','status','reason','request_slots'}}
            stored['worker_results']=stored['workers']
            for name, worker in stored['workers'].items():state['nodes'][name]=worker
            state['result']=stored;state['lifecycle']='terminal';state['budget']=budget.snapshot()
            self.store.write(state)
            for name, worker in result['workers'].items():
                self.store.trace(state['run_id'], name, worker['status'], error_category=(worker.get('error') or {}).get('category'))
            self.store.trace(state['run_id'], 'supervisor', result['status'], elapsed_seconds=time.monotonic()-started)
            # The initial response and terminal resume share the persisted,
            # privacy-filtered projection. Answer/data/evidence are unchanged.
            budget.remaining();return stored
        except BaseException as error:
            budget.run_id=state['run_id']
            if budget.database_result is not None:
                budget.database_result.run_id=state['run_id']
            state['lifecycle']='interrupted';state['budget']=budget.snapshot();self.store.write(state)
            self.store.trace(state['run_id'], 'supervisor', 'interrupted', error_category=type(error).__name__)
            raise
