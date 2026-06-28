"""AI layer: security (no PII, no key needed to fail safe) — no live API calls."""

import os

import pytest

from src import ai, data, llm


@pytest.fixture(scope="module")
def sales():
    return data.build_sales()


def test_no_api_key_means_unavailable(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    assert llm.available() is False


def test_context_contains_no_pii(sales):
    ctx = ai.build_context(sales)
    # Aggregates only — none of these raw-record fields may leak.
    customers = data.load_customers()
    sample_name = customers.iloc[0]["first_name"]
    assert sample_name not in ctx
    assert "AW000" not in ctx          # customer numbers
    assert "birthdate" not in ctx.lower()
    # But it must contain the headline aggregates.
    assert "Revenue" in ctx and "margin" in ctx


def test_empty_question_short_circuits_without_calling_api(sales, monkeypatch):
    # Even with a (fake) key, an empty question must not hit the network.
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-fake")

    def _boom(*a, **k):  # pragma: no cover - must never run
        raise AssertionError("LLM must not be called for an empty question")

    monkeypatch.setattr(ai.llm, "complete", _boom)
    assert ai.answer_question(sales, "   ") == "Please enter a question."


def test_question_is_length_capped(sales, monkeypatch):
    captured = {}

    def _capture(system, user, max_tokens):
        captured["user"] = user
        return "ok"

    monkeypatch.setattr(ai, "_cached_complete", _capture)
    ai.answer_question(sales, "x" * 5000)
    # The 5000-char question is truncated to MAX_QUESTION_CHARS in the prompt.
    assert ("x" * (ai.MAX_QUESTION_CHARS + 1)) not in captured["user"]


def test_build_context_handles_empty():
    import pandas as pd

    assert "No data" in ai.build_context(pd.DataFrame())
