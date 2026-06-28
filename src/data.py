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
