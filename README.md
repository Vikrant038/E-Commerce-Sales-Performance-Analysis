# 📊 E-Commerce Sales Performance Analysis

**Turn raw e-commerce data into decisions.** This project takes raw CRM/ERP sales extracts, builds a clean SQL data warehouse, and serves the results as an **interactive dashboard** anyone can use — no SQL required.

🔗 **Live demo:** _<add Streamlit Cloud URL>_ · 🎥 **2-min walkthrough:** _<add Loom link>_

![Dashboard screenshot](docs/screenshots/dashboard.png)
<!-- Run the app, take a screenshot, save it as docs/screenshots/dashboard.png — see docs/screenshots/README.md -->

---

## The problem
~27,700 orders, 18,500 customers and 296 products lived in six raw source tables. Useful, but unusable: no one could quickly answer *where revenue comes from, who the best customers are, or whether the business is growing.*

## What it does
- **Cleans & models the data** into a tidy star schema using a Medallion (Bronze → Silver → Gold) SQL warehouse.
- **Dashboard** with live KPIs (revenue, orders, customers, average order value, units) and filters for date, category, country, and customer segment.
- **Four views** — Overview (trends), Products, Customers, and plain-English **Insights** — all updating instantly as you filter.
- **Download** the filtered slice as CSV.

## 💡 Insights it surfaces (each with a "so what")
1. **Revenue is concentrated:** Bikes drive **96.5%** of revenue — concentration risk + diversification need.
2. **Profit hides in small categories:** Accessories earn a **62.8% margin** (vs 39% on bikes) but are only 2.4% of sales → push attach-sales.
3. **Repeat customers carry the business:** **37% of buyers generate 77% of revenue** → retention beats acquisition.
4. **The 2013 boom was returning buyers:** **64%** of the peak-year revenue came from repeat customers → protect the flywheel.
5. **Two markets dominate:** **US + Australia ≈ 62%** of revenue.
6. **December seasonality:** strongest month is **1.8×** the February trough → time stock & campaigns.

Headline: **€29.4M revenue · €11.7M profit · 39.8% margin · €1,061 AOV.** → Full write-up in [`docs/INSIGHTS.md`](docs/INSIGHTS.md) · 2-min demo script in [`docs/VIDEO_SCRIPT.md`](docs/VIDEO_SCRIPT.md).

---

## ▶️ Run it locally
```bash
# from this folder
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
streamlit run streamlit_app.py     # opens http://localhost:8501
```

## ☁️ Deploy free (Streamlit Community Cloud)
1. Push this repo to GitHub.
2. Go to [share.streamlit.io](https://share.streamlit.io) → **New app**.
3. Pick the repo and set the main file to **`streamlit_app.py`**.
4. Deploy — you get a public URL to paste above and share with clients.

---

## 🧱 How it's built
```
datasets/        Bronze (raw) → Silver (cleaned) → Gold (star schema) CSV exports
scripts/         12 T-SQL analytical scripts (exploration → ranking → time-series → segmentation)
streamlit_app.py Dashboard entry point
src/             data.py (load/filter) · insights.py (live metrics) · charts.py (Plotly figures)
docs/            Case study + screenshot/Loom assets
```

The dashboard reads the **Gold-layer** CSVs (already cleaned by the SQL pipeline) and never touches Bronze/Silver — the same separation the warehouse enforces. Each chart mirrors a SQL script (e.g. category mix ↔ `10_part_to_whole_analysis.sql`, top products ↔ `05_ranking_analysis.sql`).

**Tech:** T-SQL (SQL Server / Medallion) · Python · pandas · Streamlit · Plotly.

---

## 🌟 About Me
Hi! I'm **Vikrant Yadav** — I build AI automation & data systems for businesses. On a mission to make working with data enjoyable and engaging.

[![LinkedIn](https://img.shields.io/badge/LinkedIn-0077B5?style=for-the-badge&logo=linkedin&logoColor=white)](https://www.linkedin.com/in/vikrant-ydata/)
