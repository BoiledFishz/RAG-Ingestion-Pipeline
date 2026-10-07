"""Isolated offline judges; held-out bodies never enter design or Workers.

Prints only aggregate progress. Original scores/answers and approved facts are
not rewritten. New first scores are explicitly machine scores, not human ones.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import logging
import random
import sys
import time
import urllib.request
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.judge_frozen_answers_a2 import RUBRIC, quote_catalog, rating_schema
from evaluation_protocol.statistics import wilson

LOGGER = logging.getLogger(__name__)
OUT = ROOT / 'evals/project2-v1/ch12/second_scoring'
PACK = ROOT / 'evals/project2-v1/ch12/independent_review/human_template.json'


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path: Path):
    return json.loads(path.read_text(encoding='utf-8'))


def save(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')


def cohen_kappa(first: list[int], second: list[int]) -> dict:
    if not first or len(first) != len(second):
        raise ValueError('Paired ordinal scores required')
    n = len(first); matches = sum(a == b for a, b in zip(first, second))
    a, b = Counter(first), Counter(second)
    chance = sum(a[x]*b[x] for x in (0, 1, 2))/(n*n)
    return {'agreement_numerator': matches, 'agreement_denominator': n,
            'agreement': matches/n, 'agreement_wilson95': wilson(matches, n),
            'kappa': (matches/n-chance)/(1-chance) if chance < 1 else None,
            'undefined_reason': 'constant unanimous scores' if chance == 1 else None}


def validate_scores(item: dict, scores: dict) -> list[dict]:
    if set(scores) != {f['fact_id'] for f in item['required_facts']}:
        raise ValueError('Frozen fact identities differ')
    result = []
    for fact in item['required_facts']:
        value = scores[fact['fact_id']];score = value['score'];quote = value['answer_quote']
        if type(score) is not int or score not in (0, 1, 2):
            raise ValueError('Invalid 0/1/2 score')
        if (score and (not quote or quote not in item['answer_body'])) or (not score and quote):
            raise ValueError('Positive score requires literal answer-body quote')
        if not value.get('reason'):
            raise ValueError('Missing independent reason')
        result.append({'fact_id': fact['fact_id'], **value})
    return result


def register() -> dict:
    OUT.mkdir(parents=True, exist_ok=True)
    if sha(PACK) != PACK.with_suffix('.json.sha256').read_text().strip():
        raise ValueError('Offline answer pack changed')
    config = read(ROOT/'evals/protocol_v0/baseline_v0.config.json')['environment']
    base = config['AGENT_OLLAMA_URL']
    if not base.startswith(('http://localhost:', 'http://127.0.0.1:')):
        raise ValueError('Only local models authorized')
    with urllib.request.urlopen(base+'/api/tags', timeout=10) as response:
        inventory = json.load(response)
    models = {x['name']: x['digest'] for x in inventory['models']}
    generator, first, second = config['AGENT_MODEL'], 'llama3.2:3b', 'qwen2.5:3b'
    if any(m not in models for m in (generator, first, second)) or len({models[m] for m in (generator, first, second)}) != 3:
        raise ValueError('Three distinct installed model digests required')
    plan = {'pack_sha256': sha(PACK), 'script_sha256': sha(Path(__file__)),
            'authorization_sha256': sha(ROOT/'specs/project2/approval_appendix_2026-10-05_continue.md'),
            'base_url': base, 'models': {m: models[m] for m in (generator, first, second)},
            'generator': generator, 'first': first, 'second': second,
            'first_score_provenance': 'new LLM ratings of previously unscored bodies; no human ratings invented',
            'rubric': RUBRIC, 'options': {'temperature': 0, 'num_ctx': 8192, 'num_predict': 900},
            'seed': 20261005, 'audit_selection': '16 observations stratified by partition/empty-body; plus <=8 largest ordinal disagreements; tie by hash',
            'independence': 'judges never see each other scores; qwen3b shares generator family, disclose correlated-bias limitation',
            'scope': 'offline body-only scoring; no source-context scoring; held-out not rerun or used for design',
            'score_attempts': 1, 'missing_or_failed_scores': 'remain missing; never replaced by 0',
            'inventory': inventory}
    path = OUT/'plan.json'
    if path.exists() and read(path) != plan:
        raise ValueError('Registered judging plan changed')
    if not path.exists():
        save(path, plan);path.with_suffix('.json.sha256').write_text(sha(path)+'\n')
    return plan


def judge(plan: dict, model: str, items: list[dict]) -> list[dict]:
    output = OUT/(model.replace(':', '_')+'.jsonl')
    if output.exists():
        existing = [json.loads(x) for x in output.read_text(encoding='utf-8').splitlines()]
        if len(existing) != len(items):
            raise ValueError('Interrupted judge run cannot be silently filled or rerun')
        return existing
    results = []
    with output.open('x', encoding='utf-8') as handle:
        for index, item in enumerate(items, 1):
            catalog = quote_catalog(item['answer_body']);facts = item['required_facts']
            prompt = RUBRIC+'\n'+json.dumps({'facts': [{'fact_id': x['fact_id'], 'text': x['text']} for x in facts],
                         'ANSWER_BODY': item['answer_body'], 'ANSWER_QUOTE_CATALOG': catalog}, ensure_ascii=False)
            request = urllib.request.Request(plan['base_url']+'/api/chat', data=json.dumps({
                'model': model, 'stream': False, 'format': rating_schema(facts, catalog),
                'messages': [{'role': 'user', 'content': prompt}], 'options': plan['options']}).encode(),
                headers={'Content-Type': 'application/json'})
            result = {'index': index, 'model': model, 'model_digest': plan['models'][model],
                      'partition': item['partition'], 'answer_sha256': item['answer_sha256'],
                      'definition_sha256': item['definition_content_sha256'],
                      'prompt_sha256': hashlib.sha256(prompt.encode()).hexdigest(), 'valid': False}
            started = time.monotonic()
            try:
                with urllib.request.urlopen(request, timeout=180) as response:
                    raw = json.load(response)
                if raw.get('done_reason') == 'length':
                    raise ValueError('Truncated judging output')
                parsed = json.loads(raw['message']['content'])
                decoded = {key: {'score': value['score'], 'answer_quote': catalog.get(value['answer_quote_id'], ''), 'reason': value['reason']}
                           for key, value in parsed.items()}
                if any(v['score'] > 0 and v['answer_quote_id'] not in catalog for v in parsed.values()):
                    raise ValueError('Unknown body quote ID')
                result['scores'] = validate_scores(item, decoded)
                result.update(valid=True, prompt_tokens=raw.get('prompt_eval_count'), output_tokens=raw.get('eval_count'))
            except Exception as error:
                result['error_category'] = type(error).__name__
            result['elapsed_seconds'] = time.monotonic()-started
            handle.write(json.dumps(result, ensure_ascii=False)+'\n');handle.flush();results.append(result)
            LOGGER.info('Offline judge %s %d/%d valid=%s elapsed=%.2f', model, index, len(items), result['valid'], result['elapsed_seconds'])
    return results


def summarize(plan: dict, items: list[dict], first: list[dict], second: list[dict]) -> dict:
    a = [];b = [];disagreements = [];observations = [];coverage = defaultdict(list)
    for item, one, two in zip(items, first, second):
        if not one['valid'] or not two['valid']:
            continue
        pairs = list(zip(one['scores'], two['scores']))
        distance = sum(abs(x['score']-y['score']) for x, y in pairs)
        for x, y in pairs:
            a.append(x['score']);b.append(y['score'])
            if x['score'] != y['score']:
                disagreements.append({'index': one['index'], 'partition': item['partition'],
                                      'fact_id': x['fact_id'], 'first': x, 'second': y})
        for obs in item['observations']:
            observations.append({'index': one['index'], 'partition': item['partition'], 'repeat': obs['repeat'],
                                 'empty': not item['answer_body'].strip(), 'distance': distance,
                                 'answer_sha256': item['answer_sha256']})
        for name, score in (('first', one), ('second', two)):
            coverage[(item['partition'], name)].append({'index': one['index'], 'single_fact_exception': item['single_fact_exception'],
                                                       'numerator': sum(x['score'] for x in score['scores']), 'denominator': 2*len(score['scores'])})
    strata = defaultdict(list)
    for obs in observations:
        strata[(obs['partition'], obs['empty'])].append(obs)
    rng = random.Random(plan['seed']);queues = []
    for key in sorted(strata):
        rows = sorted(strata[key], key=lambda x: (x['index'], x['repeat']));rng.shuffle(rows);queues.append(rows)
    selected = []
    while len(selected) < min(16, len(observations)):
        for rows in queues:
            if rows and len(selected) < 16:
                selected.append({**rows.pop(), 'selection': 'fixed_seed_stratified'})
    seen = {(x['index'], x['repeat']) for x in selected}
    extra = [x for x in sorted(observations, key=lambda x: (-x['distance'], x['answer_sha256'], x['repeat']))
             if x['distance'] and (x['index'], x['repeat']) not in seen][:8]
    selected += [{**x, 'selection': 'largest_disagreement'} for x in extra]
    # Private review packet is never emitted in model/tool output.
    audit = [{'selection': x['selection'], 'repeat': x['repeat'], 'index': x['index'],
              'item': items[x['index']-1], 'first_scores': first[x['index']-1].get('scores'),
              'second_scores': second[x['index']-1].get('scores'), 'human_scores': None, 'human_reviewed': False} for x in selected]
    save(OUT/'human_spot_check.json', {'status': '人工抽检待办', 'seed': plan['seed'], 'items': audit,
                                      'must_not_be_used_for_design': True})
    agreement = cohen_kappa(a, b) if a else None
    # Cluster bootstrap by independently rated answer body; repetitions are not new annotations.
    clusters = [[(x['score'], y['score']) for x, y in zip(one.get('scores', []), two.get('scores', []))]
                for one, two in zip(first, second) if one['valid'] and two['valid']]
    bootstrap = [];rng = random.Random(plan['seed'])
    if clusters:
        for _ in range(2000):
            sample = [pair for group in rng.choices(clusters, k=len(clusters)) for pair in group]
            value = cohen_kappa([x for x, _ in sample], [y for _, y in sample])['kappa']
            if value is not None:bootstrap.append(value)
    bootstrap.sort()
    if agreement:
        agreement['kappa_cluster_bootstrap95'] = [bootstrap[int(.025*len(bootstrap))], bootstrap[int(.975*len(bootstrap))-1]] if bootstrap else None
        agreement['ci_limitation'] = 'Wilson fact interval is descriptive; bootstrap clusters by answer for dependence'
    by_partition = Counter(x['partition'] for item in items for x in [{'partition': item['partition']}] for _ in item['observations'])
    result = {'status': 'completed' if len(observations) == sum(by_partition.values()) else 'incomplete',
              'description': 'LLM 第二评分完成；人工抽检待办；不称独立人工评分' if len(observations) == sum(by_partition.values()) else 'LLM评分存在失败，未完成；人工抽检待办',
              'answer_observations': dict(by_partition), 'paired_observations': len(observations), 'unique_bodies': len(items),
              'first_model': plan['first'], 'second_model': plan['second'], 'first_score_provenance': plan['first_score_provenance'],
              'human_review_status': '待办', 'human_independent_ratings_completed': False, 'agreement': agreement,
              'disagreements': disagreements, 'spot_check_random': sum(x['selection']=='fixed_seed_stratified' for x in selected),
              'spot_check_extra': len(extra), 'coverage': {f'{p}/{m}': rows for (p, m), rows in coverage.items()},
              'plan_sha256': sha(OUT/'plan.json'), 'limitation': plan['independence'], 'heldout_inference_calls': 0}
    save(OUT/'summary.json', result)
    return result


def main() -> int:
    argparse.ArgumentParser(description=__doc__).parse_args()
    plan = register();items = read(PACK)['items']
    first = judge(plan, plan['first'], items);second = judge(plan, plan['second'], items)
    result = summarize(plan, items, first, second)
    LOGGER.info('Offline rating status=%s bodies=%d observations=%d kappa=%s', result['status'], len(items), result['paired_observations'], (result['agreement'] or {}).get('kappa'))
    return 0 if result['status']=='completed' else 1


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
    raise SystemExit(main())
