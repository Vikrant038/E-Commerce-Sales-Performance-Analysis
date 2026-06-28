# agent.md — E-Commerce Sales Performance Analysis

> **Purpose**: Guide a new developer/AI agent on how to work with this project. It has **two layers**: (1) a **T-SQL analytics** pipeline using a Medallion (Bronze/Silver/Gold) data warehouse, and (2) a **Python/Streamlit dashboard** that consumes the Gold-layer CSVs for an interactive demo. It is **not a mobile app**.

---

## 1. Project Identity

| Property | Value |
|----------|-------|
| **Project Name** | sql-data-analytics-project (E-Commerce Sales Performance Analysis) |
| **Type** | SQL Data Analytics / Data Warehouse |
| **Author** | Vikrant Yadav |
| **Description** | A comprehensive collection of T-SQL scripts for exploring, segmenting, and analyzing e-commerce sales data. Implements a Medallion architecture with Bronze (raw), Silver (cleaned), and Gold (dimensional model + analytical views) layers. |
| **Target Audience** | BI specialists, data analysts, data engineers |

---

## 2. Tech Stack & Build Setup

| Component | Details |
|-----------|---------|
| **Languages** | T-SQL (Microsoft SQL Server dialect) · Python 3.9+ (dashboard) |
| **Syntax Indicators** | `TOP n`, `DATETRUNC()`, `FORMAT()`, `IF OBJECT_ID() IS NOT NULL DROP VIEW`, `GO` batches, `DATEDIFF()`, `GETDATE()` |
| **Dashboard Stack** | Streamlit + Plotly + pandas (`streamlit_app.py`, `src/`) reading `datasets/gold.*` |
| **Data Format** | CSV files (datasets/) + SQL scripts (scripts/) |
| **Architecture Pattern** | Medallion / Bronze-Silver-Gold Data Warehouse + read-only Streamlit BI layer |
| **Database Objects** | Tables (CSV-backed), Views (`gold.report_customers`, `gold.report_products`) |

### Dashboard commands
```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
streamlit run streamlit_app.py     # http://localhost:8501
```
Deploy free on Streamlit Community Cloud (main file: `streamlit_app.py`).

### Key Commands
> This project has **no build system** (no Gradle, Maven, npm, etc.). Execution is manual:
- Open SQL Server Management Studio (SSMS) / Azure Data Studio / `sqlcmd`
- Run scripts in `scripts/` in numerical order (01 → 12) or as needed
- Gold-layer CSVs in `datasets/gold.*` are the **output** of the pipeline; Silver/Bronze CSVs are intermediate/raw inputs

### Dependencies
| Dependency | Version | Purpose |
|------------|---------|---------|
| SQL Server / Azure SQL | Any recent | Execution engine for T-SQL |
| (Optional) Python/pandas | — | For ad-hoc CSV inspection or automation |

### Special Setup
- No environment variables, secrets, or certificates required
- CSV files are self-contained in `datasets/`
- Scripts assume a database context where `gold` schema exists (or `CREATE SCHEMA gold` first)

---

## 3. Architecture & Project Structure

```
E-Commerce-Sales-Performance-Analysis/
├── datasets/
│   ├── bronze.*          # Raw source extracts (CRM, ERP)
│   ├── silver.*          # Cleaned, standardized
│   └── gold.*            # Dimensional model + analytical views (CSV exports)
├── streamlit_app.py      # Dashboard entry point (Streamlit Cloud auto-detects this)
├── src/                  # Python modules
│   ├── data.py           #   cached loaders + filters over datasets/gold.*
│   ├── clean.py          #   Bronze→Silver→Gold cleaning pipeline (mirrors the SQL)
│   ├── insights.py       #   live KPI + 6 action-oriented insight computations
│   ├── charts.py         #   Plotly figure builders (mirror the SQL scripts)
│   ├── llm.py            #   provider-agnostic LLM client (Anthropic; key from secrets/env)
│   └── ai.py             #   PII-free "ask the data" + executive summary
├── tests/                # pytest suite (run in CI): data quality, KPIs, cleaning, AI safety
├── .github/workflows/ci.yml  # GitHub Actions: pip install + pytest on push/PR
├── docs/
│   ├── INSIGHTS.md       #   one-page case study
│   ├── VIDEO_SCRIPT.md   #   2-min Loom script
│   └── screenshots/      #   screenshot/GIF/Loom assets for README
├── requirements.txt      # streamlit, pandas, plotly, numpy, anthropic
├── requirements-dev.txt  # + pytest
├── .streamlit/config.toml
├── .streamlit/secrets.toml.example  # template for the optional AI key
├── scripts/
│   ├── 01_dimension_exploration.sql
│   ├── 02_range_exploration.sql
│   ├── 03_measure_exploration.sql
│   ├── 04_magnitude_analysis.sql
│   ├── 05_ranking_analysis.sql
│   ├── 06_change_over_time_analysis.sql
│   ├── 07_cummulative_analysis.sql
│   ├── 08_performance_analysis.sql
│   ├── 09_data_segmentation.sql
│   ├── 10_part_to_whole_analysis.sql
│   ├── 11_report_customer.sql
│   └── 12_report_products.sql
├── README.md
└── .git/
```

### Data Flow (Medallion)
```
Source Systems (CRM, ERP)
        │
        ▼
   Bronze Layer          ← Raw CSV (bronze.crm_*, bronze.erp_*)
   (landing zone)
        │  Clean, dedupe, standardize types
        ▼
   Silver Layer          ← silver.crm_*, silver.erp_*
   (conformed)
        │  Star-schema modeling, surrogate keys
        ▼
   Gold Layer            ← dim_customers, dim_products, fact_sales
   (analytics-ready)          report_customers (view), report_products (view)
        │
        ▼
   Analytical Scripts (01–12) → Insights / Dashboards
```

### Navigation / Script Execution Order
- **01–03**: Exploration (dimensions, ranges, measures)
- **04–05**: Magnitude & Ranking (top/bottom performers)
- **06–08**: Time-series (change over time, cumulative, YoY/MoM)
- **09**: Segmentation (customer & product cohorts)
- **10**: Part-to-whole (contribution analysis)
- **11–12**: Materialized analytical views (report_customers, report_products)

---

## 4. Coding Standards & Conventions

| Area | Convention |
|------|------------|
| **File Naming** | `NN_descriptive_name.sql` (zero-padded, snake_case) |
| **SQL Formatting** | Uppercase keywords (`SELECT`, `FROM`, `WHERE`), 4-space indent, CTEs with comments |
| **Comments** | Header block with `Purpose`, section markers (`/*─── 1) Base Query ───*/`) |
| **Naming** | Tables: `snake_case`; Columns: `snake_case`; Views: `report_*`; CTEs: descriptive (`base_query`, `customer_aggregation`) |
| **Date Handling** | Use `DATETRUNC(month, col)` for grouping; `DATEDIFF(month, start, end)` for intervals |
| **Window Functions** | `RANK()`, `LAG()`, `AVG() OVER (PARTITION BY ...)` for ranking & YoY |
| **Null Safety** | `NULLIF(quantity, 0)`, `CASE WHEN denom = 0 THEN 0 ELSE num/denom END` |
| **View Creation** | `IF OBJECT_ID('gold.report_X', 'V') IS NOT NULL DROP VIEW ...; GO` then `CREATE VIEW` |

---

## 5. Testing Strategy

| Aspect | Approach |
|--------|----------|
| **Framework** | `pytest` for the Python layer (`tests/`), run automatically in CI; manual SSMS verification for SQL |
| **Run tests** | `pip install -r requirements-dev.txt && pytest -q` (23 tests) |
| **Validation** | Run scripts in SSMS/Azure Data Studio; inspect row counts, spot-check known values |
| **Regression** | `tests/test_clean.py` asserts the Python pipeline reproduces committed Gold (rows exact, revenue within 0.01%) |
| **Data Quality** | Tests enforce no NULL PK/FK and fact→dim integrity; AI tests assert no PII leaves in the LLM context |
| **App smoke test** | `streamlit.testing.v1.AppTest` renders the whole app headless with no exceptions |

### Adding a New Analytical Script
1. Create `scripts/NN_new_analysis.sql` (next number)
2. Follow header comment convention (`Purpose`, `Highlights`)
3. Use CTEs for modularity; anchor to `gold.*` tables
4. Test in isolation, then add to execution sequence documentation

---

## 6. Agent Work Rules

### Adding a New Feature (Analysis)
1. **Identify the analytical question** (e.g., "cohort retention by acquisition month")
2. **Determine layer**: Gold (star schema) is the source; never query Bronze/Silver directly
3. **Write script** following naming (`NN_`) and header convention
4. **Use CTEs** for readability: `base_query` → `aggregations` → `final_select`
5. **Handle nulls & division-by-zero** explicitly
6. **Verify** against known CSV exports in `datasets/gold.*`

### Fixing a Bug (Incorrect Metric)
1. Reproduce: run the offending script, note wrong output
2. Trace: check CTE intermediates; verify `gold.fact_sales` ↔ `gold.dim_*` joins
3. Fix: correct logic (e.g., `COUNT(DISTINCT order_number)` vs `COUNT(order_number)`)
4. Verify: re-run; cross-check with `datasets/gold.report_*` if applicable

### Never Do
- ❌ Hardcode literal dates (use `GETDATE()` or anchor to `MAX(order_date)`)
- ❌ Skip `NULLIF` / `CASE` guards on denominators
- ❌ Query `bronze.*` or `silver.*` in analytical scripts
- ❌ Use `SELECT *` in production views
- ❌ Assume `order_date` is never NULL (always `WHERE order_date IS NOT NULL`)
- ❌ Commit changes to `datasets/gold.*` CSVs directly — they are **generated artifacts**

### Git Conventions (if used)
- Branch: `feature/<short-desc>` or `fix/<short-desc>`
- Commit: `NN: <imperative summary>` (e.g., `05: add bottom-5 product ranking`)
- PR: Reference script number(s) affected

---

## Quick Reference: Gold Schema

```sql
-- Dimensions
gold.dim_customers   (customer_key PK, customer_id, customer_number, first_name, last_name, country, marital_status, gender, birthdate, create_date)
gold.dim_products    (product_key PK, product_id, product_number, product_name, category_id, category, subcategory, maintenance, cost, product_line, start_date)

-- Fact
gold.fact_sales      (order_number, product_key FK, customer_key FK, order_date, shipping_date, due_date, sales_amount, quantity, price)

-- Analytical Views (created by scripts 11 & 12)
gold.report_customers  -- customer KPIs, segments (VIP/Regular/New), age groups
gold.report_products   -- product KPIs, segments (High-Performer/Mid-Range/Low-Performer)
```

> **Tip**: All analytical scripts should start from `gold.fact_sales` joined to dimensions. The CSV files in `datasets/gold.*` are **exports** of these tables/views for portability.