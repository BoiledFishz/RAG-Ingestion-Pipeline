import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
sys.path.insert(0, str(ROOT / 'enterprise-ai-agent'))


def test_explicit_query_components_are_not_rejected_before_retrieval():
    from models.project2 import AnalysisRequest
    from tools.techqa_document_query import query_groups
    rows = json.loads((ROOT / 'evals/project2-v1/ch12/qa-tune/scored.json').read_text(encoding='utf-8'))
    baseline = json.loads((ROOT / 'evals/protocol_v0/runs/baseline-v0-quick/tune/runs.json').read_text(encoding='utf-8'))
    questions = {x['question_id']: x['native']['run']['trace']['original_query'] for x in baseline}
    controls = {x['question_id'] for x in json.loads((ROOT / 'evals/protocol_v0/controls.json').read_text(encoding='utf-8'))['records']}
    selected = {x['question_id'] for x in rows if x['question_id'] in controls and
                (x['result']['workers']['rag'].get('error') or {}).get('category') == 'clarification_required'}
    assert selected
    for identifier in sorted(selected):
        query = questions[identifier]
        groups = query_groups(AnalysisRequest(query=query))
        assert groups and all(phrase in query for group in groups for phrase in group)


def test_second_judge_math_and_body_quote_validation():
    from project2_second_scoring import cohen_kappa, validate_scores
    assert cohen_kappa([0, 1, 2], [0, 1, 2])['kappa'] == 1
    assert cohen_kappa([0, 0], [0, 0])['kappa'] is None
    # Score validation uses a real official-data definition and answer body.
    template = json.loads((ROOT / 'evals/project2-v1/ch12/independent_review/human_template.json').read_text(encoding='utf-8'))
    item = next(x for x in template['items'] if x['partition'] == 'tune')
    import pytest
    with pytest.raises(ValueError):
        validate_scores(item, {f['fact_id']: {'score': 2, 'answer_quote': 'not in answer', 'reason': 'bad'} for f in item['required_facts']})
def test_offline_repair_summary_refuses_incomplete_or_duplicate_slots():
    from scripts.project2_regression_diagnosis import validate_repair_slots
    import pytest
    questions = [{'record': {'QUESTION_ID': 'join-key-only'}, 'group_sha256': 'group'}]
    rows = [{'question_id': 'join-key-only', 'group_sha256': 'group', 'repeat': r} for r in (1, 2, 3)]
    validate_repair_slots(rows, questions)
    with pytest.raises(ValueError, match='incomplete'):
        validate_repair_slots(rows[:-1], questions)
    with pytest.raises(ValueError, match='duplicate'):
        validate_repair_slots([rows[0], rows[0], rows[2]], questions)
