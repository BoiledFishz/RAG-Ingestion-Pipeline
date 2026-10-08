"""Container platform and trusted transport are isolated from old defaults."""
import sys
from pathlib import Path

import pytest


def test_linux_worker_uses_running_python_without_windows_venv(tmp_path,monkeypatch):
    import agents.project2.rag_process as process
    python=tmp_path/'python';python.touch()
    monkeypatch.setattr(sys,'executable',str(python))
    assert process.native_python(tmp_path,platform='linux')==python
    with pytest.raises(FileNotFoundError):
        process.native_python(tmp_path,platform='win32')


def test_container_transport_only_accepts_local_docker_bridge():
    from agents.project2.container_transport import bridge_url
    assert bridge_url('http://host.docker.internal:11434')=='http://host.docker.internal:11434'
    for value in ['https://example.com','http://host.docker.internal:9999','http://user:secret@host.docker.internal:11434','http://host.docker.internal:11434/x']:
        with pytest.raises(ValueError):bridge_url(value)
