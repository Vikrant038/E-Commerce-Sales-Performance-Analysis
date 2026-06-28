"""
AI features: "ask the data" Q&A and an auto-generated executive summary.

Security model — this is the important part:

- The LLM **never sees raw rows or PII** (no names, birthdates, customer ids).
  It only receives a small, pre-computed *aggregate* snapshot of the currently
  filtered data (KPIs, category/segment/country/year roll-ups). That snapshot is
  built here, in ``build_context``.
- The LLM **never executes code** and has **no tools**. It does text-in/text-out
  only (see ``llm.py``), so a malicious question can't run anything.
- The user's question is length-capped and the system prompt scopes the model to
  the provided figures, refusing unrelated requests.
- Answers are cached on (question, context) so repeated/identical queries don't
  re-bill the API.
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from . import insights, llm

MAX_QUESTION_CHARS = 500

_SYSTEM = (
    "You are a precise data analyst embedded in an e-commerce sales dashboard. "
    "Answer ONLY using the figures in the DATA SNAPSHOT provided in the user "
    "message. Do not invent numbers or use outside knowledge. If the snapshot "
    "doesn't contain the answer, say so plainly. Be concise (2-4 sentences), "
    "lead with the number, and never output anything except your final answer."
)


TOP_N_IN_CONTEXT = 5


def _kpi_lines(sales: pd.DataFrame) -> list[str]:
    kpi_values = insights.kpis(sales)
    return [
        "DATA SNAPSHOT (current dashboard filter; all figures in EUR):",
        f"- Revenue: {kpi_values['revenue']:,.0f}; "
        f"Gross profit: {kpi_values['profit']:,.0f} ({kpi_values['margin']:.1f}% margin)",
        f"- Orders: {kpi_values['orders']:,}; Customers: {kpi_values['customers']:,}; "
        f"Units: {kpi_values['units']:,}; Avg order value: {kpi_values['aov']:,.0f}",
    ]


def _category_lines(sales: pd.DataFrame) -> list[str]:
    by_category = sales.groupby("category").agg(
        revenue=("sales_amount", "sum"), profit=("profit", "sum")
    ).sort_values("revenue", ascending=False)
    lines = ["- Revenue & margin by category:"]
    for category, row in by_category.iterrows():
        margin = row["profit"] / row["revenue"] * 100 if row["revenue"] else 0
        lines.append(f"    {category}: {row['revenue']:,.0f} ({margin:.0f}% margin)")
    return lines


def _segment_lines(sales: pd.DataFrame) -> list[str]:
    by_segment = sales.groupby("customer_segment").agg(
        revenue=("sales_amount", "sum"), customers=("customer_key", "nunique")
    ).sort_values("revenue", ascending=False)
    lines = ["- By customer segment (revenue / #customers):"]
    for segment, row in by_segment.iterrows():
        lines.append(f"    {segment}: {row['revenue']:,.0f} / {int(row['customers']):,}")
    return lines


def _top_line(sales: pd.DataFrame, column: str, label: str) -> str:
    top = (
        sales.groupby(column)["sales_amount"].sum()
        .sort_values(ascending=False).head(TOP_N_IN_CONTEXT)
    )
    return f"- {label}: " + ", ".join(f"{name}: {value:,.0f}" for name, value in top.items())


def build_context(sales: pd.DataFrame) -> str:
    """Compact, PII-free aggregate snapshot of the (filtered) data for the model."""
    if sales.empty:
        return "No data in the current filter."
    by_year = sales.groupby("order_year")["sales_amount"].sum()
    year_line = "- Revenue by year: " + ", ".join(
        f"{int(year)}: {value:,.0f}" for year, value in by_year.items()
    )
    lines = [
        *_kpi_lines(sales),
        *_category_lines(sales),
        *_segment_lines(sales),
        year_line,
        _top_line(sales, "country", "Top countries"),
        _top_line(sales, "product_name", "Top products"),
    ]
    return "\n".join(lines)


@st.cache_data(show_spinner=False)
def _cached_complete(system: str, user: str, max_tokens: int) -> str:
    return llm.complete(system, user, max_tokens=max_tokens)


def answer_question(sales: pd.DataFrame, question: str) -> str:
    """Answer a natural-language question about the filtered data."""
    question = (question or "").strip()[:MAX_QUESTION_CHARS]
    if not question:
        return "Please enter a question."
    context = build_context(sales)
    user = f"{context}\n\nQUESTION: {question}"
    return _cached_complete(_SYSTEM, user, 600)


def executive_summary(sales: pd.DataFrame) -> str:
    """A short, plain-English briefing of the current view."""
    context = build_context(sales)
    user = (
        f"{context}\n\nWrite a 3-4 sentence executive summary for a business "
        "owner: the headline result, the biggest opportunity, and one risk. "
        "Use specific numbers from the snapshot."
    )
    return _cached_complete(
        "You are a concise business analyst. Use only the figures provided.",
        user,
        500,
    )
