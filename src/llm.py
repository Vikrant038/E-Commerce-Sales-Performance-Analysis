"""
Provider-agnostic LLM client for the dashboard's AI features.

Design principles (deliberate, for long-term maintainability + security):

- **Pluggable provider.** The provider and model are read from config, not
  hardcoded. Anthropic (Claude) is implemented; adding OpenAI/Gemini means one
  new ``_complete_*`` function and a branch in ``complete`` — nothing else changes.
- **Secrets never touch the code or the repo.** The API key is read only from
  ``st.secrets`` or the environment. ``.streamlit/secrets.toml`` is gitignored.
- **Fails safe.** If no key is configured the whole AI surface degrades to a
  friendly notice and the rest of the dashboard keeps working — so the public
  demo never breaks on a missing key.
- **No tools, no code execution.** This module only does text-in/text-out
  completions. The model never runs code or sees raw customer rows (see ``ai.py``).
"""

from __future__ import annotations

import os
from dataclasses import dataclass

import streamlit as st

DEFAULT_PROVIDER = "anthropic"
DEFAULT_MODEL = "claude-opus-4-8"  # configurable via LLM_MODEL (e.g. claude-haiku-4-5 to cut demo cost)
MAX_OUTPUT_TOKENS = 1024


@dataclass(frozen=True)
class LLMConfig:
    provider: str
    model: str
    api_key: str | None


def _secret(name: str) -> str | None:
    """Read a setting from Streamlit secrets first, then the environment. Never log it."""
    try:
        if name in st.secrets:
            return str(st.secrets[name])
    except Exception:
        # st.secrets raises if no secrets file exists — fall through to env.
        pass
    return os.environ.get(name)


def get_config() -> LLMConfig:
    provider = (_secret("LLM_PROVIDER") or DEFAULT_PROVIDER).lower()
    model = _secret("LLM_MODEL") or DEFAULT_MODEL
    key_name = {
        "anthropic": "ANTHROPIC_API_KEY",
        "openai": "OPENAI_API_KEY",
        "gemini": "GEMINI_API_KEY",
    }.get(provider, "ANTHROPIC_API_KEY")
    return LLMConfig(provider=provider, model=model, api_key=_secret(key_name))


def available() -> bool:
    """True when an API key is configured for the selected provider."""
    return bool(get_config().api_key)


class LLMError(RuntimeError):
    """Raised on any provider failure, with a user-safe message (no secrets)."""


def complete(system: str, user: str, max_tokens: int = MAX_OUTPUT_TOKENS) -> str:
    """Single text completion. Returns the model's text, or raises LLMError."""
    cfg = get_config()
    if not cfg.api_key:
        raise LLMError("No API key configured.")
    if cfg.provider == "anthropic":
        return _complete_anthropic(cfg, system, user, max_tokens)
    raise LLMError(
        f"Provider '{cfg.provider}' is not implemented. "
        "Set LLM_PROVIDER=anthropic, or add a handler in src/llm.py."
    )


def _complete_anthropic(cfg: LLMConfig, system: str, user: str, max_tokens: int) -> str:
    try:
        import anthropic  # lazy import so the app runs without the package installed
    except ModuleNotFoundError as exc:  # pragma: no cover - import guard
        raise LLMError("The 'anthropic' package is not installed.") from exc

    client = anthropic.Anthropic(api_key=cfg.api_key)
    try:
        resp = client.messages.create(
            model=cfg.model,
            max_tokens=max_tokens,
            system=system,
            output_config={"effort": "low"},  # simple Q&A — keep latency + cost down
            messages=[{"role": "user", "content": user}],
        )
    except anthropic.APIStatusError as exc:
        raise LLMError(f"The AI service returned an error ({exc.status_code}).") from exc
    except anthropic.APIConnectionError as exc:
        raise LLMError("Could not reach the AI service. Check your connection.") from exc

    if resp.stop_reason == "refusal":
        raise LLMError("The model declined to answer that request.")
    return "".join(b.text for b in resp.content if b.type == "text").strip()
