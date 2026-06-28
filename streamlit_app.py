"""
E-Commerce Sales Performance — interactive dashboard.

Reads the gold-layer CSVs produced by the SQL pipeline (scripts/), then lets a
non-technical user explore revenue, profit, products, and customers, and read
plain-English, action-oriented insights. Built for the Freelancing Proof Pack
"Repo 1".

Run locally:   streamlit run streamlit_app.py

@size-exception: complex-jsx — this is the Streamlit page entry point (top-to-bottom
render script, ~210 lines). Business logic lives in src/*; this file only wires
widgets to those functions. @reviewer: PR review.
"""

from __future__ import annotations

import streamlit as st

from src import ai, charts, data, insights, llm

# Per-session cap on AI calls — protects a public demo from runaway API cost.
AI_CALL_LIMIT = 15

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

kpi_values = insights.kpis(filtered)
row1 = st.columns(4)
row1[0].metric("Total revenue", f"€{kpi_values['revenue']/1e6:.2f}M")
row1[1].metric("Gross profit", f"€{kpi_values['profit']/1e6:.2f}M", f"{kpi_values['margin']:.0f}% margin")
row1[2].metric("Orders", f"{kpi_values['orders']:,}")
row1[3].metric("Customers", f"{kpi_values['customers']:,}")
row2 = st.columns(4)
row2[0].metric("Avg order value", f"€{kpi_values['aov']:,.0f}")
row2[1].metric("Items / order", f"{kpi_values['items_per_order']:.2f}")
row2[2].metric("Units sold", f"{kpi_values['units']:,}")
row2[3].metric("Revenue / customer", f"€{kpi_values['revenue']/kpi_values['customers']:,.0f}")

st.markdown("---")

# ─────────────────────────────────────────────────────────────────────────────
# Tabs
# ─────────────────────────────────────────────────────────────────────────────
tab_overview, tab_products, tab_customers, tab_insights, tab_ai = st.tabs(
    ["📈 Overview", "📦 Products", "👥 Customers", "💡 Insights", "🤖 Ask the data"]
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

with tab_ai:
    st.subheader("Ask a question about this data")
    st.caption(
        "Powered by an LLM that sees **only an aggregated, PII-free snapshot** of "
        "the current filter — never raw customer records, and it runs no code."
    )

    if not llm.available():
        st.info(
            "🔒 The AI assistant is **not configured** (no API key) — the rest of "
            "the dashboard works fully without it.\n\n"
            "To enable it locally, add to `.streamlit/secrets.toml`:\n"
            "```toml\nANTHROPIC_API_KEY = \"sk-ant-...\"\n```\n"
            "On Streamlit Cloud, add the same key under **App → Settings → Secrets**."
        )
        with st.expander("See exactly what would be sent to the model"):
            st.code(ai.build_context(filtered), language="text")
    else:
        used = st.session_state.get("ai_calls", 0)
        remaining = AI_CALL_LIMIT - used
        if remaining <= 0:
            st.warning("AI request limit reached for this session. Reload to reset.")
        else:
            st.caption(f"{remaining} AI requests left this session.")
            col_q, col_s = st.columns([3, 1])
            with col_q:
                question = st.text_input(
                    "Your question",
                    placeholder="e.g. Which country grew the most in 2013?",
                    label_visibility="collapsed",
                )
            with col_s:
                summarize = st.button("📝 Summarize view", use_container_width=True)

            if st.button("Ask", type="primary") and question.strip():
                with st.spinner("Thinking…"):
                    try:
                        st.session_state["ai_calls"] = used + 1
                        st.markdown(ai.answer_question(filtered, question))
                    except llm.LLMError as exc:
                        st.error(f"AI request failed: {exc}")
            if summarize:
                with st.spinner("Summarizing…"):
                    try:
                        st.session_state["ai_calls"] = used + 1
                        st.markdown(ai.executive_summary(filtered))
                    except llm.LLMError as exc:
                        st.error(f"AI request failed: {exc}")

        with st.expander("What the model sees (aggregated snapshot)"):
            st.code(ai.build_context(filtered), language="text")

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
