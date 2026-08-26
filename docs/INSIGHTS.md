# Case Study — E-Commerce Sales Performance Analysis

<p align="left">
  <img src="https://img.shields.io/badge/T--SQL-Medallion%20Warehouse-CC292B?logo=microsoftsqlserver&logoColor=white" alt="T-SQL" />
  <img src="https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white" alt="Python" />
  <img src="https://img.shields.io/badge/Streamlit-Dashboard-FF4B4B?logo=streamlit&logoColor=white" alt="Streamlit" />
  <img src="https://img.shields.io/badge/Plotly-Analytics-3F4F75?logo=plotly&logoColor=white" alt="Plotly" />
  <img src="https://img.shields.io/badge/Tests-72%20Passing-brightgreen?logo=pytest&logoColor=white" alt="Tests" />
</p>

> One-page case study for the Freelancing Proof Pack. Format: Problem → What I built → Result → Tech. All figures are computed directly from the dataset.

## Problem
An e-commerce business had ~27,700 orders across 18,500 customers and 296 products sitting in raw CRM/ERP extracts, but no clean way to answer strategic questions: *Where does our revenue actually come from? Which categories generate true margin? Who are our high-value repeat buyers? How reliable is our fulfillment pipeline, and which items are frequently co-purchased?* The data was spread across six raw source tables with inconsistent types and surrogate keys.

## What I built
A complete, production-grade analytics system:

1. **A Medallion data warehouse (T-SQL).** Raw extracts land in a **Bronze** layer, get cleaned/standardised into a **Silver** layer, and are modelled into a **Gold** star schema (`dim_customers`, `dim_products`, `fact_sales`) plus two reporting views (`report_customers`, `report_products`). 14 analytical scripts cover exploration, ranking, time-series, segmentation, logistics fulfillment, and market basket co-occurrence analysis.
2. **An interactive Streamlit dashboard** on top of the Gold layer: live KPIs, filterable charts across 7 analytical views (Overview, Products & Profitability, Customer Intelligence, Logistics & Operations, Cross-Selling, Live Insights, and a conversational AI Assistant), plus multi-tab Excel workbooks (`.xlsx`) export.

## Result — eight insights that drive decisions

Headline numbers: **€29.4M revenue · €11.7M gross profit · 39.8% margin · €1,061 AOV · 2.18 items/order · 98.2% on-time fulfillment.**

1. **Revenue is concentrated in one category.** Bikes generate **96.5%** of all revenue; Accessories (2.4%) and Clothing (1.2%) are tiny. Within bikes, Road (49.5%) + Mountain (33.9%) dominate. → Concentration risk + a clear catalogue-diversification need.

2. **The profit lives in the small categories.** Accessories run a **62.8% gross margin** vs **39% on bikes** (39.8% overall) — yet accessories are only 2.4% of sales. → Pushing accessories as **attach/add-on items** lifts profit far more than their revenue share suggests.

3. **High-frequency cross-sell pairings.** Helmets and Bottle Cages have a **>20% attach rate** with primary bike purchases. → Implement cart checkout bundling to boost multi-item penetration.

4. **Repeat customers carry the business.** Only **37% of customers buy more than once, but they generate 77% of revenue.** → Retention (loyalty, re-order nudges) beats pure acquisition — the second purchase is where lifetime value compounds.

5. **The 2013 boom was returning customers.** Revenue peaked at **€16.3M in 2013, and 64% of that came from returning buyers** (vs ~0% in 2011–12). → The repeat-purchase flywheel, not new-customer volume, drove exponential growth.

6. **Two markets dominate.** **United States + Australia = ~62%** of revenue; UK, Germany, France, Canada split the rest. → Defend the core two; test localized growth in the long tail.

7. **High fulfillment reliability with optimization upside.** **98.2% of orders ship on time** with an average turnaround of **2.8 days**. → Target late dispatch outliers in peak seasonal months to maintain customer satisfaction.

8. **Clear seasonality pattern.** December is the strongest month and February the weakest — a **1.8× swing**. → Build inventory and marketing campaigns toward Q4; run promotional pushes to lift the Q1 trough.

## Tech
T-SQL (Microsoft SQL Server / Medallion DDL & Stored Procedures), Python 3.12, pandas, Streamlit, Plotly, openpyxl, Docker, pytest, GitHub Actions.

## Links
- **Live demo:** [Streamlit Cloud App](https://e-commerce-sales-performance-analysis.streamlit.app/)
- **Repository:** [GitHub](https://github.com/Vikrant038/E-Commerce-Sales-Performance-Analysis)

