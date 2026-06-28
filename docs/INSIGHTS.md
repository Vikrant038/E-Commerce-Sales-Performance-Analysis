# Case Study — E-Commerce Sales Performance Analysis

> One-page case study for the Freelancing Proof Pack. Format: Problem → What I built → Result → Tech. All figures are computed directly from the dataset.

## Problem
An e-commerce business had ~27,700 orders across 18,500 customers and 296 products sitting in raw CRM/ERP extracts, but no clean way to answer simple questions: *Where does our revenue actually come from? Who are our best customers? Is the business growing?* The data was spread across six raw source tables with inconsistent types and keys.

## What I built
A two-part analytics system:

1. **A Medallion data warehouse (T-SQL).** Raw extracts land in a **Bronze** layer, get cleaned/standardised into a **Silver** layer, and are modelled into a **Gold** star schema (`dim_customers`, `dim_products`, `fact_sales`) plus two reporting views (`report_customers`, `report_products`). 12 analytical scripts cover exploration, ranking, time-series, segmentation, and part-to-whole analysis.
2. **An interactive Streamlit dashboard** on top of the Gold layer: live KPIs, filterable charts (revenue trend, category mix, top products/customers, segments), and plain-English insights — so a non-technical stakeholder can self-serve.

## Result — six insights that drive decisions

Headline numbers: **€29.4M revenue · €11.7M gross profit · 39.8% margin · €1,061 AOV · 2.18 items/order.**

1. **Revenue is concentrated in one category.** Bikes generate **96.5%** of all revenue; Accessories (2.4%) and Clothing (1.2%) are tiny. Within bikes, Road (49.5%) + Mountain (33.9%) dominate. → Concentration risk + a clear catalogue-diversification need.

2. **The profit lives in the small categories.** Accessories run a **62.8% gross margin** vs **39% on bikes** (39.8% overall) — yet accessories are only 2.4% of sales. → Pushing accessories as **attach/add-on items** lifts profit far more than their revenue share suggests.

3. **Repeat customers carry the business.** Only **37% of customers buy more than once, but they generate 77% of revenue.** → Retention (loyalty, re-order nudges) beats pure acquisition — the second purchase is where the money is.

4. **The 2013 boom was returning customers.** Revenue peaked at **€16.3M in 2013, and 64% of that came from returning buyers** (vs ~0% in 2011–12). → The repeat-purchase flywheel, not new-customer volume, drove growth. Protect it.

5. **Two markets dominate.** **United States + Australia = ~62%** of revenue; UK, Germany, France, Canada split the rest. → Defend the core two; test growth in the long tail.

6. **Clear December seasonality.** December is the strongest month, February the weakest — a **1.8× swing**. → Time inventory and campaigns toward Q4; promote to lift the Q1 trough.

## Tech
T-SQL (SQL Server / Medallion architecture), Python, pandas, Streamlit, Plotly. Deployed free on Streamlit Community Cloud.

## Links
- **Live demo:** _<add Streamlit Cloud URL>_
- **2-min walkthrough (Loom):** _<add Loom link>_
- **Code:** this repository (`scripts/` = SQL pipeline, `streamlit_app.py` + `src/` = dashboard)
