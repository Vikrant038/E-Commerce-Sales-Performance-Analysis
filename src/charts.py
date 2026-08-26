"""
Plotly figure builders for the dashboard.

Each function takes the filtered sales frame and returns a ready-to-render
plotly Figure. Charts mirror the analyses in ../scripts/ so the dashboard and
the SQL tell the same story.

@size-exception: cohesive-module — a flat registry of independent figure builders
(>200 lines). Splitting into multiple files would fragment one logical concern
(the dashboard's chart catalogue) with no readability gain. @reviewer: PR review.
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


# @size-exception: config-object
# @components: the go.Pie trace spec and the go.Figure layout (title, legend, annotation)
# @cohesion: it is a single Plotly figure definition; splitting the trace from its
#   layout would scatter one chart's config across two functions and reduce readability
# @reviewer: awaiting PR review
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


def subcategory_bar(sales: pd.DataFrame, top_n: int = 8) -> go.Figure:
    """Top subcategories by revenue — one level below category."""
    top_subcategories = (
        sales.groupby("subcategory")["sales_amount"].sum()
        .sort_values(ascending=False).head(top_n).reset_index()
    )
    fig = px.bar(
        top_subcategories, x="sales_amount", y="subcategory",
        orientation="h", text_auto=".2s",
    )
    fig.update_traces(marker_color=ACCENT)
    fig.update_yaxes(title=None, categoryorder="total ascending")
    fig.update_xaxes(title="Revenue (€)", tickprefix="€")
    return _layout(fig, f"Top {top_n} subcategories by revenue")


def margin_by_category(sales: pd.DataFrame) -> go.Figure:
    """Gross margin % by category — where the profit really is."""
    by_category = sales.groupby("category").agg(
        rev=("sales_amount", "sum"), profit=("profit", "sum")
    ).reset_index()
    by_category = by_category[by_category["rev"] > 0]
    by_category["margin"] = by_category["profit"] / by_category["rev"] * 100
    by_category = by_category.sort_values("margin", ascending=False)
    fig = px.bar(by_category, x="category", y="margin", text="margin")
    fig.update_traces(marker_color="#16A085", texttemplate="%{text:.0f}%")
    fig.update_yaxes(title="Gross margin (%)", ticksuffix="%")
    fig.update_xaxes(title=None)
    return _layout(fig, "Gross margin by category")


def top_products(sales: pd.DataFrame, top_n: int = 10) -> go.Figure:
    """Top-N products by revenue — mirrors 05_ranking_analysis.sql."""
    top_by_revenue = (
        sales.groupby("product_name")["sales_amount"].sum()
        .sort_values(ascending=False).head(top_n).reset_index()
    )
    fig = px.bar(
        top_by_revenue, x="sales_amount", y="product_name",
        orientation="h", text_auto=".2s",
    )
    fig.update_traces(marker_color=ACCENT)
    fig.update_yaxes(title=None, categoryorder="total ascending")
    fig.update_xaxes(title="Revenue (€)", tickprefix="€")
    return _layout(fig, f"Top {top_n} products by revenue")


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


def top_countries(sales: pd.DataFrame, top_n: int = 10) -> go.Figure:
    """Top countries by revenue."""
    if sales.empty:
        fig = go.Figure()
        return _layout(fig, f"Top {top_n} countries by revenue")
    top_by_revenue = (
        sales.groupby("country")["sales_amount"].sum()
        .sort_values(ascending=False).head(top_n).reset_index()
    )
    fig = px.bar(
        top_by_revenue, x="sales_amount", y="country",
        orientation="h", text_auto=".2s",
    )
    fig.update_traces(marker_color=ACCENT)
    fig.update_yaxes(title=None, categoryorder="total ascending")
    fig.update_xaxes(title="Revenue (€)", tickprefix="€")
    return _layout(fig, f"Top {top_n} countries by revenue")


def choropleth_world_map(sales: pd.DataFrame) -> go.Figure:
    """Interactive world map of revenue by country."""
    if sales.empty:
        fig = go.Figure()
        return _layout(fig, "Global revenue distribution")
    country_sales = sales.groupby("country").agg(
        revenue=("sales_amount", "sum"),
        orders=("order_number", "nunique"),
        customers=("customer_key", "nunique"),
    ).reset_index()

    fig = px.choropleth(
        country_sales,
        locations="country",
        locationmode="country names",
        color="revenue",
        hover_name="country",
        hover_data={"revenue": ":,.0f", "orders": ":,", "customers": ":,"},
        color_continuous_scale="Blues",
    )
    fig.update_layout(
        geo=dict(showframe=False, showcoastlines=True, projection_type="natural earth"),
        margin=dict(l=0, r=0, t=40, b=0),
        coloraxis_colorbar=dict(title="Revenue (€)", tickprefix="€"),
    )
    return _layout(fig, "Global revenue distribution")


def margin_vs_revenue_scatter(sales: pd.DataFrame) -> go.Figure:
    """Subcategory level profit margin vs sales volume scatter plot."""
    from . import data
    sub_df = data.subcategory_profitability(sales)
    if sub_df.empty:
        fig = go.Figure()
        return _layout(fig, "Subcategory profitability: volume vs margin")

    fig = px.scatter(
        sub_df,
        x="revenue",
        y="margin",
        size="units",
        color="category",
        hover_name="subcategory",
        text="subcategory",
        color_discrete_map=CATEGORY_COLORS,
        size_max=35,
    )
    fig.update_traces(textposition="top center")
    fig.update_xaxes(title="Revenue (€)", tickprefix="€")
    fig.update_yaxes(title="Gross margin (%)", ticksuffix="%")
    return _layout(fig, "Subcategory profitability: volume vs margin")


def product_affinity_bars(sales: pd.DataFrame, top_n: int = 8) -> go.Figure:
    """Top product subcategory co-purchase pairings and attach rates."""
    from . import data
    basket = data.calculate_market_basket(sales, min_occurrences=5).head(top_n)
    if basket.empty:
        fig = go.Figure()
        return _layout(fig, "Top attach-rate pairings (co-purchases)")

    basket["pairing"] = basket["item_a"] + " + " + basket["item_b"]
    fig = px.bar(
        basket,
        x="co_occurrences",
        y="pairing",
        orientation="h",
        text="attach_rate_pct",
        color_discrete_sequence=[ACCENT],
    )
    fig.update_traces(texttemplate="%{text:.0f}% attach", textposition="outside")
    fig.update_yaxes(title=None, categoryorder="total ascending")
    fig.update_xaxes(title="Co-purchased order count")
    return _layout(fig, f"Top {top_n} attach-rate pairings (co-purchases)")


def fulfillment_on_time_gauge(sales: pd.DataFrame) -> go.Figure:
    """Gauge showing on-time delivery rate."""
    if sales.empty or "is_on_time" not in sales.columns:
        fig = go.Figure()
        return _layout(fig, "On-time delivery performance")

    total = len(sales)
    on_time_pct = (sales["is_on_time"].sum() / total * 100) if total else 0.0

    fig = go.Figure(
        go.Indicator(
            mode="gauge+number",
            value=on_time_pct,
            number=dict(suffix="%"),
            gauge=dict(
                axis=dict(range=[0, 100]),
                bar=dict(color="#27AE60" if on_time_pct >= 95 else "#E67E22"),
                steps=[
                    dict(range=[0, 90], color="#FADBD8"),
                    dict(range=[90, 95], color="#FCF3CF"),
                    dict(range=[95, 100], color="#D4EFDF"),
                ],
                threshold=dict(
                    line=dict(color="#2C3E50", width=3),
                    thickness=0.75,
                    value=95,
                ),
            ),
        )
    )
    fig.update_layout(margin=dict(l=20, r=20, t=50, b=20), height=240)
    return _layout(fig, "On-time delivery rate")


def shipping_delay_distribution(sales: pd.DataFrame) -> go.Figure:
    """Distribution of delivery dispatch turnaround days."""
    if sales.empty or "days_to_ship" not in sales.columns:
        fig = go.Figure()
        return _layout(fig, "Dispatch turnaround distribution")

    bins = [-1, 0, 2, 5, 10, float("inf")]
    labels = ["Same day (0d)", "1-2 days", "3-5 days", "6-10 days", "10+ days"]
    sales_copy = sales.copy()
    sales_copy["ship_bucket"] = pd.cut(sales_copy["days_to_ship"], bins=bins, labels=labels)
    counts = sales_copy["ship_bucket"].value_counts().reindex(labels).reset_index()
    counts.columns = ["ship_bucket", "orders"]

    fig = px.bar(counts, x="ship_bucket", y="orders", text_auto=True)
    fig.update_traces(marker_color=ACCENT)
    fig.update_xaxes(title=None)
    fig.update_yaxes(title="Order lines")
    return _layout(fig, "Dispatch turnaround (days to ship)")


def rfm_segment_distribution(sales: pd.DataFrame) -> go.Figure:
    """RFM customer segmentation counts & revenue."""
    from . import data
    rfm = data.calculate_rfm(sales)
    if rfm.empty:
        fig = go.Figure()
        return _layout(fig, "Customer RFM segmentation")

    grp = rfm.groupby("rfm_segment").agg(
        customers=("customer_key", "count"),
        monetary=("monetary", "sum"),
    ).reset_index().sort_values("customers", ascending=False)

    fig = px.bar(
        grp,
        x="rfm_segment",
        y="customers",
        color="monetary",
        color_continuous_scale="Blues",
        text="customers",
    )
    fig.update_traces(textposition="outside")
    fig.update_xaxes(title=None)
    fig.update_yaxes(title="Customer Count")
    fig.update_layout(coloraxis_colorbar=dict(title="Revenue (€)", tickprefix="€"))
    return _layout(fig, "Customer RFM segmentation")


def cohort_retention_heatmap(sales: pd.DataFrame) -> go.Figure:
    """Customer retention cohort matrix by acquisition year."""
    if sales.empty:
        fig = go.Figure()
        return _layout(fig, "Customer retention by cohort")

    first_year = sales.groupby("customer_key")["order_year"].min().rename("cohort_year")
    cohort_data = sales.merge(first_year, on="customer_key")
    cohort_pivot = (
        cohort_data.groupby(["cohort_year", "order_year"])["customer_key"]
        .nunique()
        .unstack(fill_value=0)
    )

    if cohort_pivot.empty:
        fig = go.Figure()
        return _layout(fig, "Customer retention by cohort")

    # Calculate retention % relative to cohort size (year 0)
    cohort_sizes = cohort_pivot.values.diagonal()
    retention_matrix = cohort_pivot.divide(cohort_sizes, axis=0) * 100

    fig = px.imshow(
        retention_matrix,
        labels=dict(x="Active Year", y="Cohort Acquisition Year", color="Retention %"),
        x=[str(col) for col in retention_matrix.columns],
        y=[str(idx) for idx in retention_matrix.index],
        color_continuous_scale="Blues",
        text_auto=".1f",
    )
    return _layout(fig, "Cohort retention matrix (% retained)")
