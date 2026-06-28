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


def build_context(sales: pd.DataFrame) -> str:
    """Compact, PII-free aggregate snapshot of the (filtered) data for the model."""
    if sales.empty:
        return "No data in the current filter."
    k = insights.kpis(sales)
    lines = [
        "DATA SNAPSHOT (current dashboard filter; all figures in EUR):",
        f"- Revenue: {k['revenue']:,.0f}; Gross profit: {k['profit']:,.0f} "
        f"({k['margin']:.1f}% margin)",
        f"- Orders: {k['orders']:,}; Customers: {k['customers']:,}; "
        f"Units: {k['units']:,}; Avg order value: {k['aov']:,.0f}",
    ]

    by_cat = sales.groupby("category").agg(
        revenue=("sales_amount", "sum"), profit=("profit", "sum")
    )
    lines.append("- Revenue & margin by category:")
    for cat, row in by_cat.sort_values("revenue", ascending=False).iterrows():
        margin = row["profit"] / row["revenue"] * 100 if row["revenue"] else 0
        lines.append(f"    {cat}: {row['revenue']:,.0f} ({margin:.0f}% margin)")

    by_seg = sales.groupby("customer_segment").agg(
        revenue=("sales_amount", "sum"), customers=("customer_key", "nunique")
    )
    lines.append("- By customer segment (revenue / #customers):")
    for seg, row in by_seg.sort_values("revenue", ascending=False).iterrows():
        lines.append(f"    {seg}: {row['revenue']:,.0f} / {int(row['customers']):,}")

    by_year = sales.groupby("order_year")["sales_amount"].sum()
    lines.append("- Revenue by year: " + ", ".join(
        f"{int(y)}: {v:,.0f}" for y, v in by_year.items()
    ))

    top_countries = sales.groupby("country")["sales_amount"].sum().sort_values(
        ascending=False
    ).head(5)
    lines.append("- Top countries: " + ", ".join(
        f"{c}: {v:,.0f}" for c, v in top_countries.items()
    ))

    top_products = sales.groupby("product_name")["sales_amount"].sum().sort_values(
        ascending=False
    ).head(5)
    lines.append("- Top products: " + ", ".join(
        f"{p}: {v:,.0f}" for p, v in top_products.items()
    ))
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
