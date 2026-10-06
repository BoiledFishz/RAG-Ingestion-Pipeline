"""Offline review pack retains official facts and actual answer bytes."""
import importlib.util
import json
import hashlib
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]

def load():
    spec=importlib.util.spec_from_file_location('p2_review',ROOT/'scripts/prepare_project2_quality_review.py')
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m

def test_pending_tune_answers_are_not_signed_or_changed():
    pack=load().build(ROOT,'ch12',partitions=('tune',))
    summary=json.loads((ROOT/'evals/project2-v1/ch12/qa-tune/summary.json').read_text(encoding='utf-8'))
    assert sum(len(x['observations']) for x in pack['items'])==summary['required_facts']['unscored_answer_observations']
    assert pack['status']=='pending_independent_ratings'
    for item in pack['items']:
        assert hashlib.sha256(item['answer_body'].encode()).hexdigest()==item['answer_sha256']
        assert not item['human_approved'] and not item['human_annotator']
        assert all(x['score'] is None and x['answer_quote']=='' for x in item['human_scores'])
        assert 'DOC_IDS' not in item and 'DOCUMENT' not in item
