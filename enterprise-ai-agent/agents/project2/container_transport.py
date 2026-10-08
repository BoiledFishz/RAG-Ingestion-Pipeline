"""Trusted container-to-local-host transport; no model/profile changes."""
from urllib.parse import urlsplit


def bridge_url(value: str) -> str:
    parts=urlsplit(value)
    if (parts.scheme!='http' or parts.hostname!='host.docker.internal' or parts.port!=11434
            or parts.username or parts.password or parts.path not in {'','/'} or parts.query or parts.fragment):
        raise ValueError('Only local Docker bridge Ollama transport is registered')
    return 'http://host.docker.internal:11434'
