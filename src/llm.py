"""
Provider-agnostic LLM client for the dashboard's AI features.

Supports **Anthropic (Claude), OpenAI, and Google Gemini**. The active provider
is chosen by config, or auto-detected from whichever API key is present — so the
operator just drops in any one key and it works.

Design principles (deliberate, for security + maintainability):

- **Secrets never touch the code or the repo.** Keys are read only from
  ``st.secrets`` or the environment. ``.streamlit/secrets.toml`` is gitignored,
  and keys are never logged (GUARDRAILS 1.4 / 6.4).
- **Fails safe.** With no key the whole AI surface degrades to a notice and the
  rest of the dashboard keeps working — the public demo never breaks.
- **Bounded calls.** A request timeout and an output-token cap guard against a
  hung UI and runaway cost (GUARDRAILS Module 3.3).
- **No tools, no code execution.** Text-in / text-out only. The model never runs
  code or sees raw customer rows (see ``ai.py``).
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass

import streamlit as st

LOGGER = logging.getLogger(__name__)

MAX_OUTPUT_TOKENS = 1024
REQUEST_TIMEOUT_SECONDS = 30.0

# Provider order used for auto-detection when no provider is explicitly set.
PROVIDER_PRIORITY = ("anthropic", "openai", "gemini")
PROVIDER_KEY_NAME = {
    "anthropic": "ANTHROPIC_API_KEY",
    "openai": "OPENAI_API_KEY",
    "gemini": "GEMINI_API_KEY",
}
PROVIDER_DEFAULT_MODEL = {
    "anthropic": "claude-opus-4-8",
    "openai": "gpt-4o-mini",
    "gemini": "gemini-2.0-flash",
}


class LLMError(RuntimeError):
    """Raised on any provider failure, with a user-safe message (never a secret)."""


@dataclass(frozen=True)
class LLMConfig:
    provider: str
    model: str
    api_key: str | None


def _setting(name: str) -> str | None:
    """Read a setting from Streamlit secrets, then the environment. Never logged."""
    try:
        if name in st.secrets:
            return str(st.secrets[name])
    except Exception as exc:  # noqa: BLE001 - st.secrets raises varied types across versions
        # No secrets.toml is an expected "not configured" path; log and fall back
        # to the environment lookup rather than swallowing silently (Pillar 0.2).
        LOGGER.debug("st.secrets unavailable for %s (%s); using env", name, type(exc).__name__)
    return os.environ.get(name)


def _detect_provider() -> str:
    """Explicit LLM_PROVIDER wins; otherwise pick the first provider with a key."""
    configured = (_setting("LLM_PROVIDER") or "").strip().lower()
    if configured in PROVIDER_KEY_NAME:
        return configured
    for candidate in PROVIDER_PRIORITY:
        if _setting(PROVIDER_KEY_NAME[candidate]):
            return candidate
    return PROVIDER_PRIORITY[0]


def get_config() -> LLMConfig:
    provider = _detect_provider()
    model = _setting("LLM_MODEL") or PROVIDER_DEFAULT_MODEL[provider]
    api_key = _setting(PROVIDER_KEY_NAME[provider])
    return LLMConfig(provider=provider, model=model, api_key=api_key)


def available() -> bool:
    """True when an API key is configured for the selected provider."""
    return bool(get_config().api_key)


def complete(system: str, user: str, max_tokens: int = MAX_OUTPUT_TOKENS) -> str:
    """Single text completion. Returns the model's text, or raises ``LLMError``."""
    config = get_config()
    if not config.api_key:
        raise LLMError("No API key configured.")
    handler = {
        "anthropic": _complete_anthropic,
        "openai": _complete_openai,
        "gemini": _complete_gemini,
    }.get(config.provider)
    if handler is None:  # pragma: no cover - guarded by _detect_provider
        raise LLMError(f"Provider '{config.provider}' is not supported.")
    return handler(config, system, user, max_tokens)


def _require(module_name: str, package_name: str):
    """Lazy-import a provider SDK, turning a missing package into a clear LLMError."""
    try:
        return __import__(module_name, fromlist=["_"])
    except ModuleNotFoundError as exc:  # pragma: no cover - import guard
        raise LLMError(f"The '{package_name}' package is not installed.") from exc


def _complete_anthropic(config: LLMConfig, system: str, user: str, max_tokens: int) -> str:
    anthropic = _require("anthropic", "anthropic")
    client = anthropic.Anthropic(api_key=config.api_key, timeout=REQUEST_TIMEOUT_SECONDS)
    try:
        response = client.messages.create(
            model=config.model,
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
    except anthropic.APIStatusError as exc:
        raise LLMError(f"The AI service returned an error ({exc.status_code}).") from exc
    except anthropic.APIError as exc:
        raise LLMError("Could not reach the AI service. Check your connection.") from exc
    if response.stop_reason == "refusal":
        raise LLMError("The model declined to answer that request.")
    return "".join(block.text for block in response.content if block.type == "text").strip()


def _complete_openai(config: LLMConfig, system: str, user: str, max_tokens: int) -> str:
    openai = _require("openai", "openai")
    client = openai.OpenAI(api_key=config.api_key, timeout=REQUEST_TIMEOUT_SECONDS)
    try:
        response = client.chat.completions.create(
            model=config.model,
            max_tokens=max_tokens,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        )
    except openai.APIStatusError as exc:
        raise LLMError(f"The AI service returned an error ({exc.status_code}).") from exc
    except openai.APIError as exc:
        raise LLMError("Could not reach the AI service. Check your connection.") from exc
    return (response.choices[0].message.content or "").strip()


def _complete_gemini(config: LLMConfig, system: str, user: str, max_tokens: int) -> str:
    genai_module = _require("google.genai", "google-genai")
    client = genai_module.Client(api_key=config.api_key)
    try:
        response = client.models.generate_content(
            model=config.model,
            contents=user,
            config={"system_instruction": system, "max_output_tokens": max_tokens},
        )
    except Exception as exc:  # google-genai raises provider-specific errors
        raise LLMError("The AI service returned an error.") from exc
    return (response.text or "").strip()
