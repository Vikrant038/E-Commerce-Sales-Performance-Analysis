"""
E-Commerce Sales Performance — interactive dashboard.

Reads the gold-layer CSVs produced by the SQL pipeline (scripts/), then lets a
non-technical user explore revenue, profit, products, customers, fulfillment logistics,
cross-selling attach rates, and read plain-English, action-oriented insights.

Run locally:   streamlit run streamlit_app.py
"""

from __future__ import annotations

import io

import pandas as pd
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
# Load Data & Filter State
# ─────────────────────────────────────────────────────────────────────────────
sales = data.build_sales()
opts = data.filter_options(sales)

if "filter_date_range" not in st.session_state:
    st.session_state["filter_date_range"] = (opts["min_date"], opts["max_date"])
if "filter_categories" not in st.session_state:
    st.session_state["filter_categories"] = []
if "filter_countries" not in st.session_state:
    st.session_state["filter_countries"] = []
if "filter_segments" not in st.session_state:
    st.session_state["filter_segments"] = []


def reset_filters_callback():
    st.session_state["filter_date_range"] = (opts["min_date"], opts["max_date"])
    st.session_state["filter_categories"] = []
    st.session_state["filter_countries"] = []
    st.session_state["filter_segments"] = []


# ─────────────────────────────────────────────────────────────────────────────
# Sidebar filters
# ─────────────────────────────────────────────────────────────────────────────
st.sidebar.header("🔎 Filters")
date_range = st.sidebar.date_input(
    "Order date range",
    key="filter_date_range",
    min_value=opts["min_date"],
    max_value=opts["max_date"],
)
sel_categories = st.sidebar.multiselect(
    "Category", opts["categories"], key="filter_categories"
)
sel_countries = st.sidebar.multiselect(
    "Country", opts["countries"], key="filter_countries"
)
sel_segments = st.sidebar.multiselect(
    "Customer segment", opts["segments"], key="filter_segments"
)

st.sidebar.button("↺ Reset filters", on_click=reset_filters_callback, use_container_width=True)

st.sidebar.markdown("---")
st.sidebar.caption(
    "**Data:** gold-layer CSV exports from a Medallion (Bronze→Silver→Gold) "
    "T-SQL warehouse. See `scripts/` for the SQL pipeline and `docs/INSIGHTS.md` "
    "for the full case study."
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
    "Use the sidebar to slice the data — every chart, insight, and logistics metric updates live."
)

if filtered.empty:
    st.warning("No data matches the current filters. Widen your selection.")
    st.stop()

kpi_values = insights.kpis(filtered)
logistics = data.logistics_kpis(filtered)

row1 = st.columns(4)
row1[0].metric("Total revenue", f"€{kpi_values['revenue']/1e6:.2f}M")
row1[1].metric("Gross profit", f"€{kpi_values['profit']/1e6:.2f}M", f"{kpi_values['margin']:.0f}% margin")
row1[2].metric("Orders", f"{kpi_values['orders']:,}")
row1[3].metric("Customers", f"{kpi_values['customers']:,}")

row2 = st.columns(4)
row2[0].metric("Avg order value", f"€{kpi_values['aov']:,.0f}")
row2[1].metric("Items / order", f"{kpi_values['items_per_order']:.2f}")
row2[2].metric("On-Time Delivery", f"{logistics['on_time_rate']:.1f}%")
row2[3].metric("Avg Dispatch Time", f"{logistics['avg_days_to_ship']:.1f} days")

st.markdown("---")

# ─────────────────────────────────────────────────────────────────────────────
# Tabs
# ─────────────────────────────────────────────────────────────────────────────
(
    tab_overview,
    tab_products,
    tab_customers,
    tab_logistics,
    tab_basket,
    tab_insights,
    tab_ai,
) = st.tabs(
    [
        "📈 Overview",
        "📦 Products & Profitability",
        "👥 Customer Intelligence",
        "🚚 Logistics & Operations",
        "🛒 Cross-Selling",
        "💡 Insights",
        "🤖 Ask the Data",
    ]
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
    st.plotly_chart(
        charts.margin_vs_revenue_scatter(filtered), use_container_width=True, key="pr_scatter"
    )
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
    st.plotly_chart(charts.choropleth_world_map(filtered), use_container_width=True, key="cu_map")
    col_a, col_b = st.columns(2)
    with col_a:
        st.plotly_chart(charts.rfm_segment_distribution(filtered), use_container_width=True, key="cu_rfm")
    with col_b:
        st.plotly_chart(charts.cohort_retention_heatmap(filtered), use_container_width=True, key="cu_cohort")
    col_c, col_d = st.columns(2)
    with col_c:
        st.plotly_chart(charts.age_groups(filtered), use_container_width=True, key="cu_age")
    with col_d:
        st.plotly_chart(charts.top_countries(filtered), use_container_width=True, key="cu_country")

with tab_logistics:
    col_a, col_b = st.columns([1, 2])
    with col_a:
        st.plotly_chart(charts.fulfillment_on_time_gauge(filtered), use_container_width=True, key="log_gauge")
    with col_b:
        st.plotly_chart(charts.shipping_delay_distribution(filtered), use_container_width=True, key="log_dist")

with tab_basket:
    st.subheader("Market Basket & Product Affinity")
    st.caption("Identify items frequently purchased together within multi-line customer orders.")
    st.plotly_chart(charts.product_affinity_bars(filtered), use_container_width=True, key="bsk_pairs")

with tab_insights:
    st.subheader("What the data is telling us")
    st.caption("Computed live from the current filter — change a filter and these update.")
    cards = insights.all_insights(filtered)
    cols = st.columns(2)
    for i, ins in enumerate(cards):
        with cols[i % 2]:
            with st.container(border=True):
                st.markdown(f"#### {ins['icon']} {ins['title']}")
                st.markdown(f"<h2 style='margin:0;color:#2E86DE'>{ins['metric']}</h2>", unsafe_allow_html=True)
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
            "To enable it locally, add to `.streamlit/secrets.toml` or `.env`:\n"
            "```toml\nANTHROPIC_API_KEY = \"sk-ant-...\"\n```\n"
            "On Streamlit Cloud, add the same key under **App → Settings → Secrets**."
        )
        with st.expander("See exactly what would be sent to the model"):
            st.code(ai.build_context(filtered), language="text")
    else:
        used = st.session_state.get("ai_calls", 0)
        remaining = AI_CALL_LIMIT - used
        st.caption(f"{remaining} of {AI_CALL_LIMIT} AI requests left this session.")

        if st.button("📝 Generate Executive Summary for current view", use_container_width=True):
            if remaining <= 0:
                st.warning("AI request limit reached for this session. Reload to reset.")
            else:
                with st.spinner("Analyzing executive summary…"):
                    try:
                        st.session_state["ai_calls"] = used + 1
                        summary_res = ai.executive_summary(filtered)
                        st.session_state.setdefault("messages", []).append(
                            {"role": "user", "content": "Generate executive summary for this view"}
                        )
                        st.session_state["messages"].append(
                            {"role": "assistant", "content": summary_res}
                        )
                    except llm.LLMError as exc:
                        st.error(f"AI request failed: {exc}")

        # Render conversation history
        for msg in st.session_state.get("messages", []):
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

        if prompt := st.chat_input("Ask a question (e.g. Which category has the highest margin?)"):
            if remaining <= 0:
                st.warning("AI request limit reached for this session.")
            else:
                st.session_state.setdefault("messages", []).append({"role": "user", "content": prompt})
                with st.chat_message("user"):
                    st.markdown(prompt)

                with st.chat_message("assistant"):
                    with st.spinner("Thinking…"):
                        try:
                            st.session_state["ai_calls"] = used + 1
                            answer = ai.answer_question(filtered, prompt)
                            st.markdown(answer)
                            st.session_state["messages"].append({"role": "assistant", "content": answer})
                        except llm.LLMError as exc:
                            st.error(f"AI request failed: {exc}")

        with st.expander("What the model sees (aggregated snapshot)"):
            st.code(ai.build_context(filtered), language="text")

# ─────────────────────────────────────────────────────────────────────────────
# Multi-Format Downloads
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("---")
col_d1, col_d2 = st.columns(2)
with col_d1:
    st.download_button(
        "⬇️ Download Filtered Data (CSV)",
        data=filtered.to_csv(index=False).encode("utf-8"),
        file_name="filtered_sales.csv",
        mime="text/csv",
        use_container_width=True,
    )

with col_d2:
    # Excel multi-tab buffer
    excel_buffer = io.BytesIO()
    with pd.ExcelWriter(excel_buffer, engine="openpyxl") as writer:
        filtered.to_excel(writer, sheet_name="Filtered_Sales", index=False)
        summary_df = pd.DataFrame([kpi_values])
        summary_df.to_excel(writer, sheet_name="KPI_Summary", index=False)
        sub_df = data.subcategory_profitability(filtered)
        sub_df.to_excel(writer, sheet_name="Subcategories", index=False)
    excel_buffer.seek(0)

    st.download_button(
        "📊 Download Multi-Tab Report (Excel .xlsx)",
        data=excel_buffer.getvalue(),
        file_name="sales_performance_report.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True,
    )

st.caption("Built by Vikrant Yadav · Streamlit + Plotly on a T-SQL Medallion warehouse.")
