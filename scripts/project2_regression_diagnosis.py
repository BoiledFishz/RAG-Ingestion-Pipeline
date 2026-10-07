"""Tune/control-only bounded diagnosis and single-change follow-up.

No held-out answer files are read. QA identifiers are discovered from frozen
records and used only for joins/scoring, never forwarded to Workers.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import logging
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT));sys.path.insert(0, str(ROOT/'scripts'))
from project2_stage_eval import select_questions, online_question, invoke, retrieved_ids, reuse_fact_ratings, source_lock
from evaluation_protocol.statistics import metric
from evaluation_protocol.runner import document_id, body_f1

OUT = ROOT/'evals/project2-v1/ch12/regression_repair1'


def read(path: Path):
    return json.loads(path.read_text(encoding='utf-8'))


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')


def diagnose() -> dict:
    directory = ROOT/'evals/project2-v1/ch12/qa-tune'
    prior_path = ROOT/'evals/protocol_v0/runs/baseline-v0-quick/tune/runs.json'
    source = read(directory/'scored.json');summary = read(directory/'summary.json')
    control_path = ROOT/'evals/protocol_v0/controls.json'
    controls = {x['question_id'] for x in read(control_path)['records']}
    baseline = {(x['question_id'], x['repeat']): x for x in read(prior_path)}
    regressions = [x for x in summary['regression_items'] if x['question_id'] in controls]
    failed_pairs = {(x['question_id'], x['repeat']) for x in regressions}
    identifiers = sorted({x['question_id'] for x in regressions});items = []
    for identifier in identifiers:
        observations = []
        for row in source:
            if row['question_id'] != identifier:continue
            result = row['result'];rag = result['workers']['rag'];payload = rag['payload']
            old = baseline[(identifier, row['repeat'])];native = old['native']['run']
            error = (rag.get('error') or {}).get('category');subtype = 'no_decline'
            category = None
            if (identifier, row['repeat']) in failed_pairs:
                if rag['status']=='timeout':
                    category = '预算/超时导致的partial或timeout';subtype = error
                elif error=='clarification_required':
                    category = '检索结果变化';subtype = 'Project2_request_slot_adapter_rejected_before_retrieval'
                elif payload.get('pipeline', {}).get('candidate_ids') != old['native'].get('pipeline', {}).get('candidate_ids'):
                    category = '检索结果变化';subtype = 'candidate_order_differs'
                elif payload.get('trace', {}).get('evidence') != native.get('trace', {}).get('evidence'):
                    category = '证据映射或上下文压缩变化';subtype = 'evidence_trace_differs'
                else:
                    category = '回答生成变化';subtype = 'body_differs'
            observations.append({'repeat': row['repeat'], 'regressed': (identifier, row['repeat']) in failed_pairs,
                'category': category, 'subtype': subtype, 'overall_status': result['status'], 'rag_status': rag['status'],
                'error': rag.get('error'), 'usage': result['usage'], 'elapsed_seconds': row['elapsed_seconds'],
                'trace_id': result['trace_id'], 'trace': payload.get('trace'),
                'trace_absence': 'RAG did not start or deadline cancelled before child result' if not payload.get('trace') else None,
                'pipeline': payload.get('pipeline'), 'source_lineage': payload.get('source_lineage'),
                'v0_trace': native.get('trace'), 'v0_pipeline': old['native'].get('pipeline'),
                'v0_body_sha256': hashlib.sha256(native['response']['answer'].encode()).hexdigest(),
                'current_body_sha256': hashlib.sha256(payload.get('answer', '').encode()).hexdigest(),
                'metric_comparison': {k: {'v0': old[k], 'current': row[k]} for k in ('recall_at_5', 'recall_at_10', 'mrr', 'body_token_f1')},
                'scoring_missing': any(x['question_id']==identifier and x['repeat']==row['repeat'] for x in summary['required_facts']['unscored']),
                'evidence_file': (directory/'scored.json').relative_to(ROOT).as_posix()})
        categories = Counter(x['category'] for x in observations if x['category'])
        primary = categories.most_common(1)[0][0]
        repair = primary=='检索结果变化' and all(x['subtype'] in {'no_decline', 'Project2_request_slot_adapter_rejected_before_retrieval'} for x in observations)
        items.append({'question_id': identifier, 'primary_category': primary, 'observations': observations,
                      'repair_eligible': repair, 'decision': 'literal-component extraction fallback; no gold or aliases' if repair else 'frozen wall-clock budget/model variance; not changed'})
    value = {'status': 'diagnosed', 'partition': 'tune/control only', 'heldout_bodies_read': False,
             'control_regressed_questions': len(items), 'control_regressed_question_repeats': len(failed_pairs),
             'primary_attribution_distribution': dict(Counter(x['primary_category'] for x in items)),
             'observed_attribution_distribution': dict(Counter(x['category'] for item in items for x in item['observations'] if x['category'])),
             'items': items, 'sources': {p.relative_to(ROOT).as_posix(): sha(p) for p in (directory/'scored.json', directory/'summary.json', prior_path, control_path)},
             'requested_categories': ['预算/超时导致的partial或timeout', '检索结果变化', '证据映射或上下文压缩变化', '回答生成变化', '评分缺失'],
             'scope': '仅 tune/对照集，非 held-out 验证', 'maximum_repair_rounds': 2}
    path = ROOT/'audit/project2-v1/regression_diagnosis.json'
    if path.exists() and read(path)!=value:raise ValueError('Registered diagnosis differs')
    save(path, value)
    return value


def repair_eval() -> dict:
    questions = select_questions(ROOT, 'tune');OUT.mkdir(parents=True, exist_ok=True)
    plan = {'repair_round': 1, 'change': 'request-slots-v1.1 literal acronym/internal-capital fallback only',
            'scope': '仅 tune/对照集，非 held-out 验证', 'heldout_calls': 0, 'repeats': 3,
            'online_files': {name: sha(ROOT/name) for name in read(ROOT/'evals/project2-v1/ch12/stage.plan.json')['online_files']},
            'query_projection': 'official TITLE+QUESTION only; no gold/label/target IDs',
            'question_groups': [x['group_sha256'] for x in questions],
            'diagnosis_sha256': sha(ROOT/'audit/project2-v1/regression_diagnosis.json'),
            'original_ch12_plan_sha256': sha(ROOT/'evals/project2-v1/ch12/stage.plan.json')}
    if (OUT/'plan.json').exists():raise ValueError('One bounded tune repair run already registered')
    save(OUT/'plan.json', plan)
    tasks = [{'question_id': x['record']['QUESTION_ID'], 'group_sha256': x['group_sha256'], 'body': online_question(x['record'])} for x in questions]
    rows = invoke(ROOT, tasks, OUT/'requests.jsonl', 'ch12-repair1')
    return summarize_repair(rows)


def validate_repair_slots(rows: list[dict], questions: list[dict]) -> None:
    expected = {(x['record']['QUESTION_ID'], r, x['group_sha256']) for x in questions for r in (1, 2, 3)}
    observed = [(x['question_id'], x['repeat'], x['group_sha256']) for x in rows]
    if len(observed) != len(set(observed)):
        raise ValueError('duplicate repair slots; no selective rerun permitted')
    if set(observed) != expected:
        raise ValueError('incomplete repair slots; no score may claim complete')


def summarize_repair(rows: list[dict] | None = None) -> dict:
    """Offline scoring only; recover complete records after teardown failure."""
    questions = select_questions(ROOT, 'tune')
    plan = read(OUT/'plan.json')
    if any(sha(ROOT/name) != digest for name, digest in plan['online_files'].items()):
        raise ValueError('repair online sources changed after registration')
    if plan['question_groups'] != [x['group_sha256'] for x in questions]:
        raise ValueError('registered tune/control questions changed')
    if rows is None:
        rows = [json.loads(line) for line in (OUT/'requests.jsonl').read_text(encoding='utf-8').splitlines()]
    validate_repair_slots(rows, questions)
    # Gold first enters here, only after all retrieval/generation is finished.
    lookup = {x['record']['QUESTION_ID']: x['record'] for x in questions}
    primary = set(read(ROOT/'splits.json')['partitions']['tune']['quick_question_ids'])
    for row in rows:
        record = lookup[row['question_id']];data = row['result'] or {};rag = data.get('workers', {}).get('rag', {})
        payload = rag.get('payload', {});ids = retrieved_ids(rag);target = record['DOCUMENT'] if record['ANSWERABLE']=='Y' else None
        row.update({'label': record['ANSWERABLE'], 'primary': row['question_id'] in primary,
                    'recall_at_5': int(target in [document_id(x) for x in ids[:5]]) if target else None,
                    'recall_at_10': int(target in [document_id(x) for x in ids[:10]]) if target else None,
                    'mrr': next((1/i for i, x in enumerate(ids, 1) if document_id(x)==target), 0) if target else None,
                    'correct_document_cited': int(any(document_id(x['chunk_id'])==target for x in payload.get('sources', []))) if target else None,
                    'body_token_f1': body_f1(payload.get('answer', ''), record['ANSWER']) if target else None,
                    'n_refusal_proxy': int(rag.get('status')=='no_data') if not target else None,
                    'complete': int(rag.get('status')=='completed'), 'partial': int(rag.get('status')=='partial')})
    save(OUT/'scored.json', rows)
    old = {(x['question_id'], x['repeat']): x for x in read(ROOT/'evals/protocol_v0/runs/baseline-v0-quick/tune/runs.json')}
    controls = {x['question_id'] for x in read(ROOT/'evals/protocol_v0/controls.json')['records']}
    declines = [{'question_id': x['question_id'], 'repeat': x['repeat'], 'metric': key, 'v0': old[(x['question_id'], x['repeat'])][key], 'current': x[key]}
                for x in rows if (x['question_id'], x['repeat']) in old
                for key in ('recall_at_5', 'recall_at_10', 'mrr', 'body_token_f1')
                if x[key] is not None and x[key] < old[(x['question_id'], x['repeat'])][key]]
    chosen = [x for x in rows if x['primary']]
    summary = {'status': 'measured', 'scope': plan['scope'], 'repeats': 3, 'heldout_calls': 0,
               'requests': len(rows), 'offline_recovery': True,
               'lifecycle_limitation': 'Original invocation exited nonzero at service teardown: Windows denied owned process termination; all preregistered slots retained, no inference rerun',
               'metrics': {k: metric(chosen, k, binary=k not in {'mrr', 'body_token_f1'}) for k in ('recall_at_5', 'recall_at_10', 'mrr', 'complete', 'partial', 'body_token_f1', 'n_refusal_proxy')},
               'regression_items': declines,
               'control_regressed_questions': len({x['question_id'] for x in declines if x['question_id'] in controls}),
               'control_regressed_question_repeats': len({(x['question_id'], x['repeat']) for x in declines if x['question_id'] in controls}),
               'required_facts': reuse_fact_ratings(ROOT, 'tune', rows),
               'state_distribution': dict(Counter((x['result'] or {}).get('status', 'failed') for x in rows)),
               'plan_sha256': sha(OUT/'plan.json'), 'raw_sha256': sha(OUT/'requests.jsonl')}
    save(OUT/'summary.json', summary)
    return summary


if __name__=='__main__':
    ap = argparse.ArgumentParser(description=__doc__);ap.add_argument('--repair-eval', action='store_true');ap.add_argument('--summarize-repair', action='store_true');args = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
    result = diagnose()
    logging.info('Diagnosed %d questions / %d repetitions; attribution=%s', result['control_regressed_questions'], result['control_regressed_question_repeats'], result['primary_attribution_distribution'])
    if args.repair_eval:repair_eval()
    if args.summarize_repair:summarize_repair()
