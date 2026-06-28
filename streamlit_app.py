"""
E-Commerce Sales Performance — interactive dashboard.

Reads the gold-layer CSVs produced by the SQL pipeline (scripts/), then lets a
non-technical user explore revenue, profit, products, and customers, and read
plain-English, action-oriented insights. Built for the Freelancing Proof Pack
"Repo 1".

Run locally:   streamlit run streamlit_app.py
"""

from __future__ import annotations

import streamlit as st

from src import charts, data, insights

st.set_page_config(
    page_title="E-Commerce Sales Performance",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────────────────────────────────────
# Load
# ─────────────────────────────────────────────────────────────────────────────
sales = data.build_sales()
opts = data.filter_options(sales)

# ─────────────────────────────────────────────────────────────────────────────
# Sidebar filters
# ─────────────────────────────────────────────────────────────────────────────
st.sidebar.header("🔎 Filters")
date_range = st.sidebar.date_input(
    "Order date range",
    value=(opts["min_date"], opts["max_date"]),
    min_value=opts["min_date"],
    max_value=opts["max_date"],
)
sel_categories = st.sidebar.multiselect("Category", opts["categories"])
sel_countries = st.sidebar.multiselect("Country", opts["countries"])
sel_segments = st.sidebar.multiselect("Customer segment", opts["segments"])

if st.sidebar.button("↺ Reset filters", use_container_width=True):
    st.rerun()

st.sidebar.markdown("---")
st.sidebar.caption(
    "**Data:** gold-layer CSV exports from a Medallion (Bronze→Silver→Gold) "
    "T-SQL warehouse. See `scripts/` for the SQL pipeline and `docs/INSIGHTS.md` "
    "for the full write-up."
)

filtered = data.apply_filters(
    sales, date_range, sel_categories, sel_countries, sel_segments
)

# ─────────────────────────────────────────────────────────────────────────────
# Header + KPIs
# ─────────────────────────────────────────────────────────────────────────────
st.title("📊 E-Commerce Sales Performance")
st.caption(
    "Interactive analytics over ~27.7K orders · 18.5K customers · 296 products. "
    "Use the sidebar to slice the data — every chart and insight updates live."
)

if filtered.empty:
    st.warning("No data matches the current filters. Widen your selection.")
    st.stop()

k = insights.kpis(filtered)
row1 = st.columns(4)
row1[0].metric("Total revenue", f"€{k['revenue']/1e6:.2f}M")
row1[1].metric("Gross profit", f"€{k['profit']/1e6:.2f}M", f"{k['margin']:.0f}% margin")
row1[2].metric("Orders", f"{k['orders']:,}")
row1[3].metric("Customers", f"{k['customers']:,}")
row2 = st.columns(4)
row2[0].metric("Avg order value", f"€{k['aov']:,.0f}")
row2[1].metric("Items / order", f"{k['items_per_order']:.2f}")
row2[2].metric("Units sold", f"{k['units']:,}")
row2[3].metric("Revenue / customer", f"€{k['revenue']/k['customers']:,.0f}")

st.markdown("---")

# ─────────────────────────────────────────────────────────────────────────────
# Tabs
# ─────────────────────────────────────────────────────────────────────────────
tab_overview, tab_products, tab_customers, tab_insights = st.tabs(
    ["📈 Overview", "📦 Products", "👥 Customers", "💡 Insights"]
)

with tab_overview:
    st.plotly_chart(charts.monthly_trend(filtered), use_container_width=True, key="ov_trend")
    col_a, col_b = st.columns([3, 2])
    with col_a:
        st.plotly_chart(charts.yearly_revenue(filtered), use_container_width=True, key="ov_year")
    with col_b:
        st.plotly_chart(charts.category_donut(filtered), use_container_width=True, key="ov_donut")
    st.plotly_chart(charts.new_vs_returning(filtered), use_container_width=True, key="ov_newret")
    st.info(
        "ℹ️ The first and last months (Dec 2010, Jan 2014) are partial periods, "
        "so the curve dips at both ends — that's a data cut-off, not a sales drop."
    )

with tab_products:
    col_a, col_b = st.columns(2)
    with col_a:
        st.plotly_chart(charts.top_products(filtered), use_container_width=True, key="pr_top")
    with col_b:
        st.plotly_chart(charts.subcategory_bar(filtered), use_container_width=True, key="pr_sub")
    col_c, col_d = st.columns(2)
    with col_c:
        st.plotly_chart(charts.margin_by_category(filtered), use_container_width=True, key="pr_margin")
    with col_d:
        st.plotly_chart(charts.cost_segmentation(filtered), use_container_width=True, key="pr_cost")

with tab_customers:
    col_a, col_b = st.columns(2)
    with col_a:
        st.plotly_chart(charts.segment_split(filtered), use_container_width=True, key="cu_seg")
    with col_b:
        st.plotly_chart(charts.age_groups(filtered), use_container_width=True, key="cu_age")
    col_c, col_d = st.columns(2)
    with col_c:
        st.plotly_chart(charts.top_countries(filtered), use_container_width=True, key="cu_country")
    with col_d:
        st.plotly_chart(charts.seasonality(filtered), use_container_width=True, key="cu_season")

with tab_insights:
    st.subheader("What the data is telling us")
    st.caption("Computed live from the current filter — change a filter and these update.")
    cards = insights.all_insights(filtered)
    cols = st.columns(2)
    for i, ins in enumerate(cards):
        with cols[i % 2]:
            with st.container(border=True):
                st.markdown(f"#### {ins['icon']} {ins['title']}")
                st.markdown(f"<h2 style='margin:0;color:#2E86DE'>{ins['metric']}</h2>",
                            unsafe_allow_html=True)
                st.write(ins["takeaway"])
                st.success(f"**Action:** {ins['action']}")

# ─────────────────────────────────────────────────────────────────────────────
# Download
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("---")
st.download_button(
    "⬇️ Download filtered data (CSV)",
    data=filtered.to_csv(index=False).encode("utf-8"),
    file_name="filtered_sales.csv",
    mime="text/csv",
)
st.caption(
    "Built by Vikrant Yadav · Streamlit + Plotly on a T-SQL Medallion warehouse."
)
