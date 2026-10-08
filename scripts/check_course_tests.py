"""Run the existing three isolated project suites; no evaluation selection."""
from __future__ import annotations

import json
import argparse
import logging
import os
import subprocess
import sys
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / 'audit/project2-course-completion-20261007'
LOGGER = logging.getLogger(__name__)


def run(round_number: int = 0) -> int:
    if round_number not in {0,1,2}:raise ValueError('At most two repair rounds')
    folder=AUDIT if round_number==0 else AUDIT/f'test_repair_round{round_number}'
    folder.mkdir(parents=True,exist_ok=True)
    receipt = {'started_at': datetime.now(timezone.utc).isoformat(),
               'kind': 'existing project automated tests, not a golden-dataset evaluation',
               'heldout_evaluation_started': False, 'projects': [], 'status': 'running'}
    AUDIT.mkdir(exist_ok=True)
    target = folder / 'course_tests.json'
    if target.exists():raise FileExistsError('Never overwrite a test round')

    def save() -> None:
        target.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

    save()
    for name, project in [('root', ROOT), ('enterprise', ROOT / 'enterprise-ai-agent'),
                          ('agentic', ROOT / 'agentic-rag-homework')]:
        xml = folder / f'{name}.junit.xml'
        log = folder / f'{name}.pytest.log'
        if xml.exists() or log.exists():
            raise ValueError('Do not overwrite a completed suite record')
        command = [sys.executable, '-m', 'pytest', f'--junitxml={xml}', '-q']
        LOGGER.info('Starting existing %s test suite', name)
        environment = {**os.environ, 'PYTHONIOENCODING': 'utf-8', 'PYTHONUTF8': '1',
                       'PYTHONPATH': os.pathsep.join((str(project), str(ROOT), str(ROOT / 'src'), str(ROOT / 'scripts')))}
        with log.open('w', encoding='utf-8') as output:
            process = subprocess.run(command, cwd=project, env=environment,
                                     stdout=output, stderr=subprocess.STDOUT, check=False)
        suites = ET.parse(xml).getroot().iter('testsuite') if xml.exists() else []
        totals = {key: 0 for key in ('tests', 'failures', 'errors', 'skipped')}
        for suite in suites:
            for key in totals:
                totals[key] += int(suite.attrib.get(key, 0))
        failures = []
        if xml.exists():
            for case in ET.parse(xml).getroot().iter('testcase'):
                if case.find('failure') is not None or case.find('error') is not None:
                    failures.append({'classname': case.attrib.get('classname'),
                                     'name': case.attrib.get('name')})
        receipt['projects'].append({'project': name, 'exit_code': process.returncode,
                                    'status': 'passed' if process.returncode == 0 else 'failed',
                                    'totals': totals, 'failure_checks': failures,
                                    'evidence_file': xml.relative_to(ROOT).as_posix(),
                                    'log_file': log.relative_to(ROOT).as_posix()})
        save()
        LOGGER.info('Existing %s tests: exit=%d, %s', name, process.returncode, totals)
    receipt['status'] = 'passed' if all(item['exit_code'] == 0 for item in receipt['projects']) else 'failed'
    receipt['finished_at'] = datetime.now(timezone.utc).isoformat()
    save()
    return int(receipt['status'] != 'passed')


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(levelname)s %(message)s')
    parser=argparse.ArgumentParser();parser.add_argument('--round',type=int,default=0)
    raise SystemExit(run(parser.parse_args().round))
