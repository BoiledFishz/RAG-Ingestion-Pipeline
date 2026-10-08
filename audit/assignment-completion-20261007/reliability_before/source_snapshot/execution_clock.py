"""Durable cumulative active time, excluding downtime; frozen attempt limits remain."""
from __future__ import annotations
import hashlib
import json
import logging
import math
import time
from pathlib import Path
from threading import Event, Thread
from uuid import uuid4
from agents.project2.budget import Budget, BudgetExceeded

LOGGER=logging.getLogger(__name__)

def load_policy(root: Path,version: str='v0.3.2') -> dict:
    if version not in {'v0.3.2','v0.3.3'}:raise ValueError('Unregistered execution policy')
    docs=root/'specs/project2'/version
    manifest=json.loads((docs/'version_manifest.json').read_text(encoding='utf-8'))
    path=docs/'recovery_accounting.json';digest=hashlib.sha256(path.read_bytes()).hexdigest()
    if manifest['files']['recovery_accounting.json']!=digest:raise ValueError('Recovery policy changed after registration')
    policy=json.loads(path.read_text(encoding='utf-8'))
    limit=90 if version=='v0.3.3' else 37.941018
    if (policy['dependency_limit'],policy['llm_limit'],policy['execution_limit_seconds'],policy['run_lifetime_seconds'])!=(19,6,limit,900):
        raise ValueError('Unauthorized recovery limits')
    return {**policy,'sha256':digest}

def validate_execution(value: dict, policy: dict) -> None:
    if (value['policy_sha256'],value['limit_seconds'],value['lifetime_seconds'],value['heartbeat_seconds'])!=(policy['sha256'],policy['execution_limit_seconds'],900,.25):
        raise ValueError('Execution policy mismatch')
    values=[value['consumed_seconds'],*[x['consumed_seconds'] for x in value['segments']]]
    if not all(type(x) in (int,float) and math.isfinite(x) and x>=0 for x in values):raise ValueError('Invalid consumed time')
    if abs(sum(values[1:])-values[0])>1e-6:raise ValueError('Execution segments do not sum')
    if any(type(x['closed']) is not bool for x in value['segments']):raise ValueError('Invalid segment state')
    if any(not x['closed'] for x in value['segments'][:-1]):raise ValueError('Multiple unclosed segments')

class ExecutionLedger:
    def __init__(self, budget: Budget, store, state: dict, *, restore: bool) -> None:
        self.budget,self.store,self.state=budget,store,state
        self.policy=store.execution_policy;limit=self.policy['execution_limit_seconds']
        self.stop_event=Event();self.closed=False
        # Include this API segment's authentication/validation, not service startup.
        self.started=budget.started_monotonic
        if restore:
            execution=state['budget']['execution'];validate_execution(execution,self.policy)
            if execution['segments'] and not execution['segments'][-1]['closed']:
                tail=execution['segments'][-1]
                tail['consumed_seconds']+=self.policy['heartbeat_seconds']
                tail['closed']=True;tail['termination']='uncertain_tail_conservatively_charged'
                execution['consumed_seconds']=sum(x['consumed_seconds'] for x in execution['segments'])
        else:
            execution={'policy_sha256':self.policy['sha256'],'limit_seconds':limit,
                'lifetime_seconds':900,'heartbeat_seconds':.25,'consumed_seconds':0.0,'segments':[]}
        self.execution=execution;self.previous=execution['consumed_seconds']
        budget.execution_ledger=self
        original=budget.snapshot
        def snapshot():
            with budget.lock:
                self.update()
                return {**original(),'execution':json.loads(json.dumps(self.execution))}
        budget.snapshot=snapshot
        # Rejections retain saved attempt/time usage; no dependency starts.
        if time.time()-state['created_at']>=900:
            raise BudgetExceeded('run_lifetime_exhausted')
        if self.previous>=limit:
            raise BudgetExceeded('cumulative_execution_exhausted')
        self.segment={'segment_id':uuid4().hex,'consumed_seconds':0.0,'closed':False}
        execution['segments'].append(self.segment)
        remaining=min(limit-self.previous,budget.limit_seconds,900-(time.time()-state['created_at']))
        # Round toward the earlier deadline; float addition must not enlarge it.
        budget.deadline=math.nextafter(self.started+remaining,-math.inf)
        budget.absolute_deadline=time.time()+budget.deadline-time.monotonic()
        self.persist()
        self.thread=Thread(target=self.heartbeat,name='p2-execution-'+state['run_id'],daemon=True)
        self.thread.start()

    def update(self) -> None:
        if self.closed or not hasattr(self,'segment'):return
        self.segment['consumed_seconds']=max(0,time.monotonic()-self.started)
        self.execution['consumed_seconds']=self.previous+self.segment['consumed_seconds']

    def persist(self) -> None:
        with self.budget.lock:
            self.state['budget']=self.budget.snapshot();self.store.write(self.state)

    def heartbeat(self) -> None:
        while not self.stop_event.wait(self.policy['heartbeat_seconds']):
            try:self.persist()
            except Exception:
                LOGGER.exception('Execution heartbeat persistence failed run=%s',self.state['run_id'])
                self.budget.cancel();break

    def finish(self) -> None:
        if self.closed:return
        self.stop_event.set()
        if hasattr(self,'thread'):self.thread.join(timeout=1)
        with self.budget.lock:
            self.update()
            if hasattr(self,'segment'):
                self.segment['closed']=True;self.segment['termination']='normal_api_exit'
            self.closed=True
            self.state['budget']=self.budget.snapshot();self.store.write(self.state)

class ExecutionLedgerBoundary:
    """Includes ASGI rendering and cancellation cleanup in the same durable segment."""
    def __init__(self, app):self.app=app
    async def __call__(self,scope,receive,send):
        try:await self.app(scope,receive,send)
        finally:
            budget=scope.get('state',{}).get('budget')
            ledger=getattr(budget,'execution_ledger',None)
            if ledger is not None:ledger.finish()
