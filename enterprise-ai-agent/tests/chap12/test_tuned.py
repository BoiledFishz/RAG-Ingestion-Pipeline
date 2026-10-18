"""Online-profile settings chosen on the tune split (real_config.json) and their precedence."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from agents.chap12 import factory
from agents.chap12.critic import critic_enabled
from models.settings import Settings


@pytest.fixture
def config(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    path = tmp_path / "real_config.json"
    path.write_text(json.dumps({"adopted": {"top_k": 12, "max_context_tokens": 3600,
                                            "critic": True}}))
    monkeypatch.setattr(factory, "TUNED", path)
    for key in ("AGENT_TOP_K", "AGENT_MAX_CONTEXT_TOKENS", "CHAP12_CRITIC"):
        monkeypatch.delenv(key, raising=False)
    return path


def test_online_profile_uses_tuned_values(config: Path) -> None:
    tuned = factory.apply_tuned(Settings(profile="ollama"))
    assert (tuned.top_k, tuned.max_context_tokens) == (12, 3600)


def test_offline_profile_is_never_changed(config: Path) -> None:
    offline = factory.apply_tuned(Settings(profile="offline"))
    assert (offline.top_k, offline.max_context_tokens) == (8, 2400)


def test_environment_wins_over_tuned_file(config: Path,
                                          monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AGENT_TOP_K", "8")
    tuned = factory.apply_tuned(Settings(profile="ollama", top_k=8))
    assert tuned.top_k == 8 and tuned.max_context_tokens == 3600


def test_missing_file_keeps_project1_defaults(tmp_path: Path,
                                              monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(factory, "TUNED", tmp_path / "absent.json")
    assert factory.apply_tuned(Settings(profile="ollama")).top_k == 8
    assert factory.tuned_config() == {}


def test_critic_default_and_env_precedence(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("CHAP12_CRITIC", raising=False)
    assert critic_enabled() is False and critic_enabled(True) is True
    monkeypatch.setenv("CHAP12_CRITIC", "off")
    assert critic_enabled(True) is False
    monkeypatch.setenv("CHAP12_CRITIC", "on")
    assert critic_enabled(False) is True
