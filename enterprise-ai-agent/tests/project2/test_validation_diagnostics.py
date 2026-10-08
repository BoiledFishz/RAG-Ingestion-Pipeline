"""A bounded input fault is locatable without logging request/credentials."""
import json
import logging
from pathlib import Path
from fastapi.testclient import TestClient


def test_invalid_operation_log_has_trace_id_and_no_query(caplog):
    from api.project2_runtime_main import create_app
    root=Path(__file__).resolve().parents[3]
    task=json.loads((root/'specs/project2/v0.3.4/task_preregistration.json').read_text(encoding='utf-8'))['samples'][0]
    with caplog.at_level(logging.WARNING):
        result=TestClient(create_app(warmup=False)).post('/v2/project2/analysis',json={'query':task['query'],'analysis_operation':'unsupported'})
    assert result.status_code==422
    assert result.json()['trace_id'] in caplog.text
    assert 'P2_INVALID_INPUT' in caplog.text
    assert task['query'] not in caplog.text
