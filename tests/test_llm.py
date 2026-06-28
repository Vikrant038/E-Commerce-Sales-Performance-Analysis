"""Multi-provider config + auto-detection (no live API calls)."""

import pytest

from src import llm

PROVIDER_KEYS = ("ANTHROPIC_API_KEY", "OPENAI_API_KEY", "GEMINI_API_KEY")
OVERRIDES = ("LLM_PROVIDER", "LLM_MODEL")


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    for name in (*PROVIDER_KEYS, *OVERRIDES):
        monkeypatch.delenv(name, raising=False)


def test_no_key_is_unavailable_and_defaults_to_anthropic():
    assert llm.available() is False
    assert llm.get_config().provider == "anthropic"


def test_single_key_selects_that_provider(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    config = llm.get_config()
    assert config.provider == "openai"
    assert config.model == llm.PROVIDER_DEFAULT_MODEL["openai"]
    assert llm.available() is True


def test_detection_follows_priority_order(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    monkeypatch.setenv("GEMINI_API_KEY", "g-test")
    # anthropic > openai > gemini — anthropic absent, so openai wins over gemini.
    assert llm.get_config().provider == "openai"
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
    assert llm.get_config().provider == "anthropic"


def test_explicit_provider_and_model_override(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "g-test")
    monkeypatch.setenv("LLM_PROVIDER", "gemini")
    monkeypatch.setenv("LLM_MODEL", "gemini-1.5-pro")
    config = llm.get_config()
    assert config.provider == "gemini"
    assert config.model == "gemini-1.5-pro"


def test_complete_without_key_raises_llm_error():
    with pytest.raises(llm.LLMError):
        llm.complete("system", "user")
