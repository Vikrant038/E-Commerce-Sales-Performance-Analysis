"""
Insight computations.

Every figure here is computed live from the (already filtered) sales frame —
no hardcoded numbers — so insights stay correct as the user filters. Each
insight returns a compact dict: a headline metric, a one-line takeaway, and an
"action" (what a business owner should *do* about it). The same logic backs
docs/INSIGHTS.md.
"""

from __future__ import annotations

import pandas as pd


def kpis(sales: pd.DataFrame) -> dict:
    """Top-line KPIs for the metric row."""
    revenue = float(sales["sales_amount"].sum())
    profit = float(sales["profit"].sum())
    orders = int(sales["order_number"].nunique())
    customers = int(sales["customer_key"].nunique())
    units = int(sales["quantity"].sum())
    return {
        "revenue": revenue,
        "profit": profit,
        "margin": (profit / revenue * 100) if revenue else 0.0,
        "orders": orders,
        "customers": customers,
        "units": units,
        "aov": revenue / orders if orders else 0.0,
        "items_per_order": units / orders if orders else 0.0,
    }


def _card(icon, title, metric, takeaway, action):
    return {
        "icon": icon,
        "title": title,
        "metric": metric,
        "takeaway": takeaway,
        "action": action,
    }


def category_concentration(sales: pd.DataFrame) -> dict:
    by_cat = sales.groupby("category")["sales_amount"].sum().sort_values(ascending=False)
    total = by_cat.sum()
    if by_cat.empty or total == 0:
        return {}
    top = by_cat.index[0]
    share = by_cat.iloc[0] / total * 100
    return _card(
        "🎯", "Revenue concentration",
        f"{share:.1f}%",
        f"**{top}** alone accounts for **{share:.1f}%** of revenue. The business "
        f"is heavily reliant on a single category.",
        "Diversify the catalogue and grow the smaller categories to reduce risk.",
    )


def margin_opportunity(sales: pd.DataFrame) -> dict:
    g = sales.groupby("category").agg(rev=("sales_amount", "sum"), profit=("profit", "sum"))
    g = g[g["rev"] > 0]
    if g.empty:
        return {}
    g["margin"] = g["profit"] / g["rev"] * 100
    total_rev = g["rev"].sum()
    best = g["margin"].idxmax()
    best_margin = g.loc[best, "margin"]
    best_share = g.loc[best, "rev"] / total_rev * 100
    overall = g["profit"].sum() / total_rev * 100
    return _card(
        "💰", "Margin opportunity",
        f"{best_margin:.0f}% margin",
        f"**{best}** earns the richest margin (**{best_margin:.0f}%** vs "
        f"{overall:.0f}% overall) but is only **{best_share:.1f}%** of sales.",
        f"Push {best.lower()} as add-on/attach items — they lift profit far more "
        f"than their revenue share suggests.",
    )


def repeat_customer_value(sales: pd.DataFrame) -> dict:
    total = float(sales["sales_amount"].sum())
    orders_per_cust = sales.groupby("customer_key")["order_number"].nunique()
    n = len(orders_per_cust)
    if n == 0 or total == 0:
        return {}
    repeat_ids = orders_per_cust[orders_per_cust >= 2].index
    repeat_share_cust = len(repeat_ids) / n * 100
    repeat_rev = sales[sales["customer_key"].isin(repeat_ids)]["sales_amount"].sum()
    repeat_rev_share = repeat_rev / total * 100
    return _card(
        "🔁", "Repeat customers carry the business",
        f"{repeat_rev_share:.0f}% of revenue",
        f"Just **{repeat_share_cust:.0f}%** of customers buy more than once, yet "
        f"they generate **{repeat_rev_share:.0f}%** of revenue.",
        "Invest in retention (loyalty, re-order nudges) over pure acquisition — "
        "a second purchase is where the money is.",
    )


def returning_growth(sales: pd.DataFrame) -> dict:
    by_year = sales.groupby("order_year")["sales_amount"].sum()
    if by_year.empty:
        return {}
    peak_year = int(by_year.idxmax())
    yr = sales[sales["order_year"] == peak_year]
    yr_total = yr["sales_amount"].sum()
    if yr_total == 0:
        return {}
    ret_share = yr[yr["is_returning"]]["sales_amount"].sum() / yr_total * 100
    return _card(
        "📈", "Growth came from returning buyers",
        f"€{by_year.max()/1e6:.1f}M peak",
        f"Revenue peaked in **{peak_year}** (€{by_year.max()/1e6:.1f}M), and "
        f"**{ret_share:.0f}%** of that came from *returning* customers — the "
        f"repeat-purchase flywheel kicking in.",
        "Protect the flywheel: keep first-time buyers engaged so they return.",
    )


def market_concentration(sales: pd.DataFrame) -> dict:
    by_country = sales.groupby("country")["sales_amount"].sum().sort_values(ascending=False)
    total = by_country.sum()
    if by_country.empty or total == 0:
        return {}
    top2 = by_country.head(2)
    top2_share = top2.sum() / total * 100
    names = " + ".join(top2.index.tolist())
    return _card(
        "🌍", "Two markets dominate",
        f"{top2_share:.0f}%",
        f"**{names}** together make up **{top2_share:.0f}%** of revenue.",
        "Defend the core two markets while testing growth in the long tail "
        "(UK, Germany, France).",
    )


def seasonality(sales: pd.DataFrame) -> dict:
    by_month = sales.groupby(sales["order_date"].dt.month)["sales_amount"].sum()
    if by_month.empty or by_month.min() == 0:
        return {}
    import calendar

    hi, lo = by_month.idxmax(), by_month.idxmin()
    ratio = by_month.max() / by_month.min()
    return _card(
        "📅", "Clear seasonal peak",
        f"{ratio:.1f}× swing",
        f"**{calendar.month_name[hi]}** is the strongest month and "
        f"**{calendar.month_name[lo]}** the weakest — a **{ratio:.1f}×** swing.",
        f"Build inventory and marketing toward {calendar.month_name[hi]}; run "
        f"promotions to lift the {calendar.month_name[lo]} trough.",
    )


def all_insights(sales: pd.DataFrame) -> list[dict]:
    """The headline insights, in display order. Empty dicts are filtered out."""
    cards = [
        category_concentration(sales),
        margin_opportunity(sales),
        repeat_customer_value(sales),
        returning_growth(sales),
        market_concentration(sales),
        seasonality(sales),
    ]
    return [c for c in cards if c]
