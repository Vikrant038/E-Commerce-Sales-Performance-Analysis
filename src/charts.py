"""
Plotly figure builders for the dashboard.

Each function takes the filtered sales frame and returns a ready-to-render
plotly Figure. Charts mirror the analyses in ../scripts/ so the dashboard and
the SQL tell the same story.
"""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

PALETTE = px.colors.qualitative.Safe
ACCENT = "#2E86DE"


def _layout(fig: go.Figure, title: str) -> go.Figure:
    fig.update_layout(
        title=title,
        margin=dict(l=10, r=10, t=50, b=10),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    return fig


def monthly_trend(sales: pd.DataFrame) -> go.Figure:
    """Monthly revenue line — mirrors 06_change_over_time_analysis.sql."""
    monthly = (
        sales.groupby("order_month")["sales_amount"].sum().reset_index()
    )
    fig = px.line(monthly, x="order_month", y="sales_amount", markers=True)
    fig.update_traces(line_color=ACCENT)
    fig.update_yaxes(title="Revenue (€)", tickprefix="€")
    fig.update_xaxes(title=None)
    return _layout(fig, "Monthly revenue trend")


def yearly_revenue(sales: pd.DataFrame) -> go.Figure:
    """Revenue by year — the YoY view."""
    yearly = sales.groupby("order_year")["sales_amount"].sum().reset_index()
    fig = px.bar(yearly, x="order_year", y="sales_amount", text_auto=".2s")
    fig.update_traces(marker_color=ACCENT)
    fig.update_yaxes(title="Revenue (€)", tickprefix="€")
    fig.update_xaxes(title=None, type="category")
    return _layout(fig, "Revenue by year")


CATEGORY_COLORS = {
    "Bikes": ACCENT,
    "Accessories": "#E07A5F",
    "Clothing": "#F2CC8F",
    "Components": "#81B29A",
}


def category_donut(sales: pd.DataFrame) -> go.Figure:
    """Category contribution — mirrors 10_part_to_whole_analysis.sql."""
    by_cat = (
        sales.groupby("category")["sales_amount"].sum().sort_values(ascending=False)
    )
    total = by_cat.sum()
    colors = [CATEGORY_COLORS.get(c, "#BDC3C7") for c in by_cat.index]
    # Pull small slices (<10%) slightly out so their labels don't collide.
    pulls = [0.0 if (v / total) >= 0.10 else 0.08 for v in by_cat.values]

    fig = go.Figure(
        go.Pie(
            labels=by_cat.index,
            values=by_cat.values,
            hole=0.58,
            sort=False,
            direction="clockwise",
            rotation=0,
            marker=dict(colors=colors, line=dict(color="white", width=2)),
            textinfo="percent",
            textposition="inside",
            insidetextorientation="horizontal",
            pull=pulls,
            hovertemplate="%{label}: €%{value:,.0f} (%{percent})<extra></extra>",
        )
    )
    fig.update_layout(
        title=dict(text="Revenue share by category", x=0.0, xanchor="left", y=0.98),
        # Hide any % label too small to fit its slice → no overflow, no collisions.
        uniformtext=dict(minsize=12, mode="hide"),
        showlegend=True,
        legend=dict(
            orientation="v", yanchor="middle", y=0.5, xanchor="left", x=1.02,
            title_text="",
        ),
        margin=dict(l=10, r=10, t=70, b=20),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        annotations=[
            dict(
                text=f"<b>€{total/1e6:.1f}M</b><br><span style='font-size:12px'>total</span>",
                x=0.5, y=0.5, xref="paper", yref="paper",
                font=dict(size=22, color="#1B2631"), showarrow=False,
            )
        ],
    )
    return fig


def new_vs_returning(sales: pd.DataFrame) -> go.Figure:
    """Stacked new vs returning revenue by year — the growth story."""
    grp = (
        sales.assign(buyer=sales["is_returning"].map({True: "Returning", False: "New"}))
        .groupby(["order_year", "buyer"])["sales_amount"].sum().reset_index()
    )
    fig = px.bar(
        grp, x="order_year", y="sales_amount", color="buyer",
        text_auto=".2s",
        color_discrete_map={"New": "#9BB8D3", "Returning": ACCENT},
    )
    fig.update_yaxes(title="Revenue (€)", tickprefix="€")
    fig.update_xaxes(title=None, type="category")
    fig.update_layout(legend_title_text="")
    return _layout(fig, "New vs returning customer revenue")


def seasonality(sales: pd.DataFrame) -> go.Figure:
    """Total revenue by calendar month — seasonality pattern."""
    import calendar

    by_month = sales.groupby(sales["order_date"].dt.month)["sales_amount"].sum()
    by_month = by_month.reindex(range(1, 13))
    df = pd.DataFrame(
        {"month": [calendar.month_abbr[m] for m in range(1, 13)], "rev": by_month.values}
    )
    fig = px.bar(df, x="month", y="rev", text_auto=".2s")
    fig.update_traces(marker_color=ACCENT)
    fig.update_yaxes(title="Revenue (€)", tickprefix="€")
    fig.update_xaxes(title=None)
    return _layout(fig, "Revenue by calendar month")


def subcategory_bar(sales: pd.DataFrame, n: int = 8) -> go.Figure:
    """Top subcategories by revenue — one level below category."""
    top = (
        sales.groupby("subcategory")["sales_amount"].sum()
        .sort_values(ascending=False).head(n).reset_index()
    )
    fig = px.bar(top, x="sales_amount", y="subcategory", orientation="h", text_auto=".2s")
    fig.update_traces(marker_color=ACCENT)
    fig.update_yaxes(title=None, categoryorder="total ascending")
    fig.update_xaxes(title="Revenue (€)", tickprefix="€")
    return _layout(fig, f"Top {n} subcategories by revenue")


def margin_by_category(sales: pd.DataFrame) -> go.Figure:
    """Gross margin % by category — where the profit really is."""
    g = sales.groupby("category").agg(
        rev=("sales_amount", "sum"), profit=("profit", "sum")
    ).reset_index()
    g = g[g["rev"] > 0]
    g["margin"] = g["profit"] / g["rev"] * 100
    g = g.sort_values("margin", ascending=False)
    fig = px.bar(g, x="category", y="margin", text="margin")
    fig.update_traces(marker_color="#16A085", texttemplate="%{text:.0f}%")
    fig.update_yaxes(title="Gross margin (%)", ticksuffix="%")
    fig.update_xaxes(title=None)
    return _layout(fig, "Gross margin by category")


def top_products(sales: pd.DataFrame, n: int = 10) -> go.Figure:
    """Top-N products by revenue — mirrors 05_ranking_analysis.sql."""
    top = (
        sales.groupby("product_name")["sales_amount"].sum()
        .sort_values(ascending=False).head(n).reset_index()
    )
    fig = px.bar(top, x="sales_amount", y="product_name", orientation="h", text_auto=".2s")
    fig.update_traces(marker_color=ACCENT)
    fig.update_yaxes(title=None, categoryorder="total ascending")
    fig.update_xaxes(title="Revenue (€)", tickprefix="€")
    return _layout(fig, f"Top {n} products by revenue")


def cost_segmentation(sales: pd.DataFrame) -> go.Figure:
    """Product count by cost band — mirrors 09_data_segmentation.sql."""
    prods = sales.drop_duplicates("product_key")[["product_key", "cost"]].copy()
    bins = [-1, 100, 500, 1000, float("inf")]
    labels = ["Below 100", "100-500", "500-1000", "Above 1000"]
    prods["cost_range"] = pd.cut(prods["cost"], bins=bins, labels=labels)
    counts = prods["cost_range"].value_counts().reindex(labels).reset_index()
    counts.columns = ["cost_range", "products"]
    fig = px.bar(counts, x="cost_range", y="products", text_auto=True)
    fig.update_traces(marker_color=ACCENT)
    fig.update_yaxes(title="Products")
    fig.update_xaxes(title="Cost band (€)")
    return _layout(fig, "Products by cost band")


def segment_split(sales: pd.DataFrame) -> go.Figure:
    """Revenue & customers by segment — mirrors 09_data_segmentation.sql."""
    seg = sales.groupby("customer_segment").agg(
        revenue=("sales_amount", "sum"),
        customers=("customer_key", "nunique"),
    ).reset_index()
    fig = px.bar(seg, x="customer_segment", y="revenue", text_auto=".2s")
    fig.update_traces(marker_color=ACCENT)
    fig.update_yaxes(title="Revenue (€)", tickprefix="€")
    fig.update_xaxes(title=None)
    return _layout(fig, "Revenue by customer segment")


def age_groups(sales: pd.DataFrame) -> go.Figure:
    """Revenue by customer age group."""
    grp = sales.groupby("age_group")["sales_amount"].sum().reset_index()
    fig = px.bar(grp, x="age_group", y="sales_amount", text_auto=".2s")
    fig.update_traces(marker_color=ACCENT)
    fig.update_yaxes(title="Revenue (€)", tickprefix="€")
    fig.update_xaxes(title=None)
    return _layout(fig, "Revenue by age group")


def top_countries(sales: pd.DataFrame, n: int = 10) -> go.Figure:
    """Top countries by revenue."""
    top = (
        sales.groupby("country")["sales_amount"].sum()
        .sort_values(ascending=False).head(n).reset_index()
    )
    fig = px.bar(top, x="sales_amount", y="country", orientation="h", text_auto=".2s")
    fig.update_traces(marker_color=ACCENT)
    fig.update_yaxes(title=None, categoryorder="total ascending")
    fig.update_xaxes(title="Revenue (€)", tickprefix="€")
    return _layout(fig, f"Top {n} countries by revenue")
