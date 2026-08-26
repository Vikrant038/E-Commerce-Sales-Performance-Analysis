"""
Data loading and filtering for the E-Commerce Sales dashboard.

The dashboard consumes the *gold* layer CSVs produced by the SQL pipeline
(see ../scripts/). These files are already cleaned, conformed, and modelled
as a star schema, so this module only loads, joins, and filters them.

All loaders are cached with @st.cache_data so the CSVs are read once per
session, not on every widget interaction.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st

# Resolve the datasets folder relative to this file so it works both locally
# and on Streamlit Community Cloud, regardless of the working directory.
DATA_DIR = Path(__file__).resolve().parent.parent / "datasets"


def _read(name: str, parse_dates: list[str] | None = None) -> pd.DataFrame:
    return pd.read_csv(DATA_DIR / name, parse_dates=parse_dates)


@st.cache_data(show_spinner="Loading sales data…")
def load_fact() -> pd.DataFrame:
    """Order-line fact table (~60K rows)."""
    return _read(
        "gold.fact_sales.csv",
        parse_dates=["order_date", "shipping_date", "due_date"],
    )


@st.cache_data
def load_customers() -> pd.DataFrame:
    """Customer dimension."""
    return _read("gold.dim_customers.csv", parse_dates=["birthdate", "create_date"])


@st.cache_data
def load_products() -> pd.DataFrame:
    """Product dimension."""
    return _read("gold.dim_products.csv", parse_dates=["start_date"])


@st.cache_data
def load_report_customers() -> pd.DataFrame:
    """Pre-aggregated customer KPI view (script 11)."""
    return _read("gold.report_customers.csv", parse_dates=["last_order_date"])


@st.cache_data
def load_report_products() -> pd.DataFrame:
    """Pre-aggregated product KPI view (script 12)."""
    return _read("gold.report_products.csv", parse_dates=["last_sale_date"])


@st.cache_data(show_spinner="Building sales model…")
def build_sales() -> pd.DataFrame:
    """
    Single denormalised sales frame: fact joined to product (category) and
    customer (country, segment). This is the working table behind every chart.
    """
    fact = load_fact()
    products = load_products()[
        ["product_key", "product_name", "category", "subcategory", "cost"]
    ]
    customers = load_customers()[["customer_key", "country", "gender", "marital_status"]]
    segments = load_report_customers()[["customer_key", "customer_segment", "age_group"]]

    sales = (
        fact.merge(products, on="product_key", how="left")
        .merge(customers, on="customer_key", how="left")
        .merge(segments, on="customer_key", how="left")
    )
    sales = sales[sales["order_date"].notna()].copy()
    sales["order_month"] = sales["order_date"].dt.to_period("M").dt.to_timestamp()
    sales["order_year"] = sales["order_date"].dt.year
    # Gross profit per line = revenue − (unit cost × quantity).
    sales["profit"] = sales["sales_amount"] - sales["cost"] * sales["quantity"]
    # First-ever order year per customer → lets us split new vs returning revenue.
    first_year = sales.groupby("customer_key")["order_year"].transform("min")
    sales["is_returning"] = sales["order_year"] > first_year

    # Logistics & fulfillment attributes
    sales["days_to_ship"] = (sales["shipping_date"] - sales["order_date"]).dt.days
    sales["is_on_time"] = sales["shipping_date"] <= sales["due_date"]
    sales["shipping_delay_days"] = (
        (sales["shipping_date"] - sales["due_date"]).dt.days.clip(lower=0)
    )
    return sales


def filter_options(sales: pd.DataFrame) -> dict:
    """Distinct values for the sidebar filter widgets."""
    return {
        "min_date": sales["order_date"].min().date(),
        "max_date": sales["order_date"].max().date(),
        "categories": sorted(sales["category"].dropna().unique().tolist()),
        "countries": sorted(sales["country"].dropna().unique().tolist()),
        "segments": sorted(sales["customer_segment"].dropna().unique().tolist()),
    }


def apply_filters(
    sales: pd.DataFrame,
    date_range: tuple,
    categories: list[str],
    countries: list[str],
    segments: list[str],
) -> pd.DataFrame:
    """Apply sidebar filters. Empty multiselect = no restriction on that field."""
    out = sales
    if date_range and len(date_range) == 2 and all(date_range):
        start, end = pd.Timestamp(date_range[0]), pd.Timestamp(date_range[1])
        out = out[(out["order_date"] >= start) & (out["order_date"] <= end)]
    if categories:
        out = out[out["category"].isin(categories)]
    if countries:
        out = out[out["country"].isin(countries)]
    if segments:
        out = out[out["customer_segment"].isin(segments)]
    return out


def calculate_rfm(sales: pd.DataFrame) -> pd.DataFrame:
    """
    Computes dynamic Recency, Frequency, and Monetary metrics for customers.
    Clusters customers into actionable segments: Champions, Loyal, Potential Loyalists,
    At Risk, Hibernating, and Promising.
    """
    if sales.empty:
        return pd.DataFrame(columns=["customer_key", "recency", "frequency", "monetary", "rfm_segment"])

    ref_date = sales["order_date"].max()
    rfm = sales.groupby("customer_key").agg(
        recency=("order_date", lambda dates: (ref_date - dates.max()).days),
        frequency=("order_number", "nunique"),
        monetary=("sales_amount", "sum"),
    ).reset_index()

    # Dynamic RFM Scoring
    r_labels = [4, 3, 2, 1]
    f_labels = [1, 2, 3, 4]
    m_labels = [1, 2, 3, 4]

    rfm["r_score"] = pd.qcut(rfm["recency"].rank(method="first"), q=4, labels=r_labels).astype(int)
    rfm["f_score"] = pd.qcut(rfm["frequency"].rank(method="first"), q=4, labels=f_labels).astype(int)
    rfm["m_score"] = pd.qcut(rfm["monetary"].rank(method="first"), q=4, labels=m_labels).astype(int)

    def _assign_segment(row: pd.Series) -> str:
        r, f, m = row["r_score"], row["f_score"], row["m_score"]
        if r >= 3 and f >= 3 and m >= 3:
            return "Champions"
        if f >= 3:
            return "Loyal Customers"
        if r >= 3 and f <= 2:
            return "Potential Loyalists"
        if r <= 2 and f >= 3:
            return "At Risk"
        if r <= 2 and f <= 2 and m >= 3:
            return "Hibernating High-Value"
        return "Standard / Casual"

    rfm["rfm_segment"] = rfm.apply(_assign_segment, axis=1)
    return rfm


def calculate_market_basket(sales: pd.DataFrame, min_occurrences: int = 5) -> pd.DataFrame:
    """
    Computes product subcategory co-occurrences in multi-item orders.
    Calculates attach rate % and co-occurrence counts.
    """
    if sales.empty:
        return pd.DataFrame(columns=["item_a", "item_b", "co_occurrences", "attach_rate_pct"])

    order_items = sales.groupby("order_number")["subcategory"].unique().reset_index()
    order_items = order_items[order_items["subcategory"].apply(len) > 1]
    if order_items.empty:
        return pd.DataFrame(columns=["item_a", "item_b", "co_occurrences", "attach_rate_pct"])

    pairs_list = []
    for subcats in order_items["subcategory"]:
        sorted_items = sorted(subcats)
        for i in range(len(sorted_items)):
            for j in range(i + 1, len(sorted_items)):
                pairs_list.append((sorted_items[i], sorted_items[j]))

    if not pairs_list:
        return pd.DataFrame(columns=["item_a", "item_b", "co_occurrences", "attach_rate_pct"])

    pairs_df = pd.DataFrame(pairs_list, columns=["item_a", "item_b"])
    counts = pairs_df.groupby(["item_a", "item_b"]).size().reset_index(name="co_occurrences")
    counts = counts[counts["co_occurrences"] >= min_occurrences].sort_values("co_occurrences", ascending=False)

    item_totals = sales.groupby("subcategory")["order_number"].nunique()
    counts["item_a_orders"] = counts["item_a"].map(item_totals)
    counts["attach_rate_pct"] = (counts["co_occurrences"] / counts["item_a_orders"] * 100).round(1)
    return counts.reset_index(drop=True)


def subcategory_profitability(sales: pd.DataFrame) -> pd.DataFrame:
    """Computes revenue, gross profit, and margin % by subcategory."""
    if sales.empty:
        return pd.DataFrame(columns=["category", "subcategory", "revenue", "profit", "margin", "units", "orders"])

    grp = sales.groupby(["category", "subcategory"]).agg(
        revenue=("sales_amount", "sum"),
        profit=("profit", "sum"),
        units=("quantity", "sum"),
        orders=("order_number", "nunique"),
    ).reset_index()

    grp["margin"] = np.where(grp["revenue"] > 0, grp["profit"] / grp["revenue"] * 100, 0.0).round(1)
    return grp.sort_values("revenue", ascending=False).reset_index(drop=True)


def logistics_kpis(sales: pd.DataFrame) -> dict:
    """Fulfillment and shipping operations KPIs."""
    if sales.empty or "is_on_time" not in sales.columns:
        return {
            "on_time_rate": 100.0,
            "avg_days_to_ship": 0.0,
            "late_orders": 0,
            "total_shipped": 0,
        }
    total = len(sales)
    on_time = int(sales["is_on_time"].sum())
    late = total - on_time
    avg_ship = float(sales["days_to_ship"].dropna().mean()) if not sales["days_to_ship"].isna().all() else 0.0
    return {
        "on_time_rate": (on_time / total * 100) if total else 0.0,
        "avg_days_to_ship": avg_ship,
        "late_orders": late,
        "total_shipped": total,
    }
