"""Preregister and measure only frozen tune tasks. No production budget bypass.

The offline measurement envelope is recorded before any calls. Its raised caps
are observation bounds, never production defaults; censored data cannot freeze
a budget. Official labels are read only to freeze the offline N scoring cohort.
No IDs, labels, reference answers or other oracle fields cross the Worker RPC.
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import logging
import math
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

LOGGER = logging.getLogger(__name__)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def registration(root: Path) -> dict[str, Any]:
    original = root / 'specs/project2/v0.2/task_preregistration.json'
    tasks = json.loads(original.read_text(encoding='utf-8'))
    tune = root / tasks['source']
    samples = [{key: row[key] for key in ('sample_id', 'query', 'query_sha256', 'analysis_operation')}
               | {'include_samples': True, 'sample_limit': 5} for row in tasks['samples']]
    # Cohort selection is offline. The online query projection contains no label.
    n_samples = []
    for row in json.loads(tune.read_text(encoding='utf-8')):
        item = row['record']
        if item['ANSWERABLE'] != 'N':
            continue
        query = item['QUESTION_TITLE'] + '\n' + item['QUESTION_TEXT']
        sha = hashlib.sha256(query.encode('utf-8')).hexdigest()
        n_samples.append({'sample_id': f'P2-N-{len(n_samples)+1:03}-' + sha[:16], 'query': query, 'query_sha256': sha,
                          'analysis_operation': 'document_count', 'include_samples': True, 'sample_limit': 5})
    n_samples.sort(key=lambda x: hashlib.sha256(f"20261005:{x['query_sha256']}".encode()).hexdigest())
    protected = {f.relative_to(root).as_posix(): digest(f) for version in ('v0.1', 'v0.2')
                 for f in (root / 'specs/project2' / version).iterdir() if f.is_file()}
    return {'version': 'project2-v0.3-calibration-v1', 'authorization_date': '2026-10-05',
            'partition': 'tune', 'seed': 20261005, 'repeats': 3, 'paths': ['rag_only', 'combination'],
            'samples': samples, 'n_samples': n_samples, 'tune_sha256': digest(tune),
            'task_registration_sha256': digest(original), 'baseline_config_sha256': digest(root / 'evals/protocol_v0/baseline_v0.config.json'),
            'protected_files': protected, 'measurement_envelope': {'attempts': 256, 'llm_calls': 64, 'seconds': 300},
            'fuse_p95': {'attempts': 32, 'llm_calls': 12},
            'production_budget_unchanged_during_measurement': True,
            'p95': 'nearest-rank ceil(0.95*n), over ALL requests on each path; choose max across paths',
            'selection': 'ceil(ceil(p95)*1.25) for call caps; seconds=1.5*p95_seconds',
            'order': 'path, original registered sample order, repeat 1..3; N set seed-hash order then repeats 1..3',
            'cache': 'existing persistent cache retained; first/second/third observed separately; no fabricated cold-cache claim',
            'attempt_definition': 'one actual SQL execute/transaction commit, HTTP send or model inference; executemany counts each issued statement; pure wrapper counted zero; retries/failures counted',
            'n_quality': 'refusal numerator includes only actual RAG no_data; failed/timeout reported separately; N gold refers to official candidate scope, not full-corpus absence',
            'heldout_calls': 0}


def p95(values: list[float]) -> float:
    if not values:
        raise ValueError('No measurements')
    return sorted(values)[math.ceil(len(values) * .95) - 1]


def select_limits(rows: list[dict[str, Any]]) -> dict[str, Any]:
    if not rows:
        return {'status': 'incomplete', 'limits': None}
    values = {key: p95([row[key] for row in rows]) for key in ('attempts', 'llm_calls', 'elapsed_seconds')}
    if values['attempts'] > 32 or values['llm_calls'] > 12:
        return {'status': 'stopped_structural_fuse', 'p95': values, 'limits': None}
    if any(row['censored'] for row in rows):
        return {'status': 'incomplete_censored', 'p95': values, 'limits': None}
    return {'status': 'selected', 'p95': values, 'limits': {'attempts': math.ceil(math.ceil(values['attempts'])*1.25),
            'llm_calls': max(1, math.ceil(math.ceil(values['llm_calls'])*1.25)),
            'seconds': round(values['elapsed_seconds']*1.5, 6)}}


def verify(root: Path, protocol: dict[str, Any]) -> None:
    for name, sha in protocol['protected_files'].items():
        if digest(root / name) != sha:
            raise ValueError(f'Protected file changed: {name}')
    if digest(root / 'evals/protocol_v0/tune.json') != protocol['tune_sha256']:
        raise ValueError('Tune changed')
    if digest(root / 'evals/protocol_v0/baseline_v0.config.json') != protocol['baseline_config_sha256']:
        raise ValueError('Baseline config changed')


async def measure(root: Path, protocol: dict[str, Any], *, resume: bool,
                  output_dir: Path | None = None, guard: Any = None,
                  freeze_output: bool = True) -> dict[str, Any]:
    sys.path.insert(0, str(root / 'enterprise-ai-agent'))
    from agents.project2.budget import Budget
    from agents.project2.policy import TrustedContext
    from agents.project2.rag_process import BoundedRAGProcess
    from agents.project2.supervisor import Supervisor
    from models.project2 import AnalysisRequest
    from tools.techqa_document_query import DatabaseWorker

    class ObservationBudget(Budget):
        """Offline only: same reserve semantics, explicit measured envelope."""
        def __init__(self):
            super().__init__()
            self.max_attempts = protocol['measurement_envelope']['attempts']
            self.max_llm_calls = protocol['measurement_envelope']['llm_calls']
            seconds = protocol['measurement_envelope']['seconds']
            self.deadline = time.monotonic() + seconds
            self.absolute_deadline = time.time() + seconds

    output = output_dir or root / 'evals/project2-v1/calibration_v03'
    output.mkdir(parents=True, exist_ok=True)
    raw = output / 'requests.jsonl'
    if raw.exists() and not resume:
        raise ValueError('Measurements exist; use explicit resume, never overwrite')
    previous = [json.loads(line) for line in raw.read_text(encoding='utf-8').splitlines()] if raw.exists() else []
    done = {(x['path'], x['sample_id'], x['repeat']) for x in previous}
    environment = json.loads((root / 'evals/protocol_v0/baseline_v0.config.json').read_text(encoding='utf-8'))['environment']
    runtime = BoundedRAGProcess(environment)
    supervisor = Supervisor(DatabaseWorker(root / '.rag_data/techqa_full.sqlite'), runtime)
    context = TrustedContext('calibration-owner', 'local', frozenset({'full'}), frozenset({'document_count', 'compare_document_counts', 'rag_explain'}))
    await runtime.start()
    try:
        for path in protocol['paths']:
            for sample in protocol['samples']:
                for repeat in range(1, protocol['repeats']+1):
                    key = (path, sample['sample_id'], repeat)
                    if key in done:
                        continue
                    if guard is not None:
                        guard.ensure_running()
                    verify(root, protocol)
                    body = {k: v for k, v in sample.items() if k not in {'sample_id', 'query_sha256'}}
                    request = AnalysisRequest(**body)
                    budget = ObservationBudget()
                    started = time.monotonic()
                    result = None
                    exception = None
                    try:
                        if path == 'rag_only':
                            result = await runtime.run(request.query, budget)
                        else:
                            result = await supervisor.run(request, context, budget)
                    except Exception as exc:
                        exception = {'category': type(exc).__name__, 'detail': str(exc)[:400]}
                    usage = budget.snapshot()
                    row = {'path': path, 'sample_id': sample['sample_id'], 'repeat': repeat,
                           'query_sha256': sample['query_sha256'], 'attempts': usage['attempts'], 'llm_calls': usage['llm_calls'],
                           'elapsed_seconds': time.monotonic()-started, 'usage': usage, 'result': result, 'exception': exception,
                           'censored': budget.cancelled or budget.attempts >= budget.max_attempts or budget.llm_calls >= budget.max_llm_calls
                           or budget.deadline <= time.monotonic() or bool((result or {}).get('budget_exceeded')),
                           'evidence_type': '真实运行', 'generated_at': datetime.now(timezone.utc).isoformat()}
                    with raw.open('a', encoding='utf-8') as handle:
                        handle.write(json.dumps(row, ensure_ascii=False) + '\n')
                    previous.append(row)
                    LOGGER.info('calibration %s %s repeat=%d attempts=%d llm=%d seconds=%.2f completed=%d/300',
                                path, sample['sample_id'], repeat, row['attempts'], row['llm_calls'], row['elapsed_seconds'], len(previous))
    finally:
        runtime.stop()
    paths = {path: select_limits([x for x in previous if x['path'] == path]) for path in protocol['paths']}
    expected = len(protocol['samples'])*protocol['repeats']*len(protocol['paths'])
    if len(previous) != expected or len(done | {(x['path'],x['sample_id'],x['repeat']) for x in previous}) != expected:
        raise ValueError('Incomplete or duplicate calibration records')
    status = 'selected' if all(x['status'] == 'selected' for x in paths.values()) else 'stopped_structural_fuse' if any(x['status'] == 'stopped_structural_fuse' for x in paths.values()) else 'incomplete_censored'
    limits = {key: max(path['limits'][key] for path in paths.values()) for key in ('attempts','llm_calls','seconds')} if status == 'selected' else None
    report = {'status': status, 'paths': paths, 'limits': limits, 'requests': len(previous), 'expected': expected,
              'protocol_sha256': digest(output / 'protocol.json'), 'raw_sha256': digest(raw),
              'heldout_calls': 0, 'complete_set_measured': True, 'production_limits_changed': False}
    save(output / 'summary.json', report)
    if freeze_output:
        save(output / 'frozen_manifest.json', {'files': {x.name: digest(x) for x in (output / 'protocol.json', raw, output / 'summary.json')}})
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--register', action='store_true')
    parser.add_argument('--measure', action='store_true')
    parser.add_argument('--resume', action='store_true')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    path = root / 'evals/project2-v1/calibration_v03/protocol.json'
    if args.register:
        candidate = registration(root)
        if path.exists() and json.loads(path.read_text(encoding='utf-8')) != candidate:
            raise ValueError('Preregistration already frozen and differs')
        if not path.exists():
            save(path, candidate)
        LOGGER.info('registered samples=%d N=%d SHA256=%s', len(candidate['samples']), len(candidate['n_samples']), digest(path))
    if args.measure:
        protocol = json.loads(path.read_text(encoding='utf-8'))
        report = asyncio.run(measure(root, protocol, resume=args.resume))
        LOGGER.info('calibration result=%s', json.dumps(report, ensure_ascii=False))
        return 0 if report['status'] == 'selected' else 1
    return 0


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
    raise SystemExit(main())
