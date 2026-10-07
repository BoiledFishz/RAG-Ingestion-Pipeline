"""The new hard ceiling cannot enlarge a deliberately shorter request budget."""
import json
from pathlib import Path
from agents.project2.budget import Budget,prepare_budget_configuration
from agents.project2.execution_clock import load_policy
from agents.project2.service_runtime import StateStore,bind_budget
from agents.project2.policy import TrustedContext
from models.project2 import AnalysisRequest
ROOT=Path(__file__).resolve().parents[3]
def test_ledger_does_not_enlarge_shorter_segment_budget(tmp_path):
    prepare_budget_configuration()  # The service validates configuration at startup.
    owner=TrustedContext('narrow-owner','local',frozenset({'full'}),frozenset({'document_count','rag_explain'}))
    query=json.loads((ROOT/'specs/project2/v0.3.3/task_preregistration.json').read_text(encoding='utf-8'))['samples'][0]['query']
    store=StateStore(tmp_path,'v033',execution_policy=load_policy(ROOT,'v0.3.3'))
    budget=Budget(seconds=.5);state=store.create(AnalysisRequest(query=query),owner,budget)
    before=budget.deadline
    bind_budget(budget,store,state)
    try:assert budget.deadline<=before
    finally:budget.execution_ledger.finish()
