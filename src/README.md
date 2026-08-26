# `src/` — application modules

**Purpose:** all Python logic behind the dashboard. `streamlit_app.py` (repo root)
only wires Streamlit widgets to these functions (layered-architecture per
`CODING_STANDARDS.md` Pillar 2).

## Quick start
```python
from src import data, insights, charts

sales = data.build_sales()                  # cached gold-layer frame
kpi_values = insights.kpis(sales)           # headline metrics
figure = charts.monthly_trend(sales)        # a Plotly figure
```

## Key files
| File | Responsibility |
| --- | --- |
| `data.py` | Cached loaders + filters over `datasets/gold.*`. |
| `clean.py` | Bronze→Silver→Gold cleaning pipeline (mirrors the SQL). |
| `insights.py` | KPI calculations + the six action-oriented insight cards. |
| `charts.py` | Plotly figure builders (one per chart; mirror the SQL scripts). |
| `llm.py` | Multi-provider LLM client (Grok [xAI] / Anthropic / OpenAI / Gemini). |
| `ai.py` | PII-free "ask the data" + executive summary, built on `llm.py`. |

## Dependencies
`pandas`, `numpy`, `plotly`, `streamlit`, `openpyxl` (always); `openai` (for Grok & OpenAI) /
`anthropic` / `google-genai` (lazily imported).

## Public API
- `data.build_sales()`, `data.filter_options()`, `data.apply_filters()`, `data.calculate_rfm()`, `data.calculate_market_basket()`, `data.logistics_kpis()`, `data.subcategory_profitability()`
- `insights.kpis()`, `insights.all_insights()`, `insights.fulfillment_efficiency()`, `insights.cross_sell_opportunity()`
- `charts.*` 19 Plotly figure builders (including choropleth, cohort heatmap, scatter, gauge)
- `clean.run_pipeline()` → `{dim_customers, dim_products, fact_sales, report_customers, report_products}`
- `ai.build_context()`, `ai.answer_question()`, `ai.executive_summary()`
- `llm.available()`, `llm.complete()`, `llm.get_config()`

## Testing
```bash
pytest -v          # from the repo root (72 tests)
```
