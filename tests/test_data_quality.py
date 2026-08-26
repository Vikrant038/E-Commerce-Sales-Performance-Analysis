"""Data-quality and KPI guarantees on the gold-backed sales model."""

import pandas as pd
import pytest

from src import data, insights


@pytest.fixture(scope="module")
def sales():
    return data.build_sales()


def test_no_missing_keys(sales):
    # Star-schema integrity: every fact row resolves to both dimensions.
    assert sales["product_key"].notna().all()
    assert sales["customer_key"].notna().all()
    assert sales["order_date"].notna().all()  # build_sales drops null order dates


def test_dimension_attributes_present(sales):
    # The joins actually populated the dimension columns we depend on.
    for col in ("category", "country", "customer_segment", "cost", "profit"):
        assert col in sales.columns
    assert sales["category"].notna().mean() > 0.99


def test_kpis_are_sane(sales):
    k = insights.kpis(sales)
    assert k["revenue"] > 0
    assert k["orders"] > 0
    assert k["customers"] > 0
    assert 0 <= k["margin"] <= 100
    assert k["aov"] == pytest.approx(k["revenue"] / k["orders"])


def test_profit_never_exceeds_revenue(sales):
    assert sales["profit"].sum() <= sales["sales_amount"].sum()


def test_filters_narrow_the_data(sales):
    opts = data.filter_options(sales)
    one_country = opts["countries"][0]
    filtered = data.apply_filters(sales, None, [], [one_country], [])
    assert (filtered["country"] == one_country).all()
    assert len(filtered) < len(sales)


def test_empty_filter_returns_empty_not_error(sales):
    # A date range with no data must yield an empty frame, not raise.
    out = data.apply_filters(
        sales,
        (pd.Timestamp("1900-01-01").date(), pd.Timestamp("1900-12-31").date()),
        [], [], [],
    )
    assert out.empty


def test_rfm_calculation(sales):
    rfm = data.calculate_rfm(sales)
    assert not rfm.empty
    assert "rfm_segment" in rfm.columns
    assert set(rfm["rfm_segment"]).issubset({
        "Champions", "Loyal Customers", "Potential Loyalists",
        "At Risk", "Hibernating High-Value", "Standard / Casual"
    })


def test_market_basket_calculation(sales):
    basket = data.calculate_market_basket(sales, min_occurrences=2)
    assert not basket.empty
    assert "attach_rate_pct" in basket.columns
    assert "co_occurrences" in basket.columns


def test_logistics_kpis_calculation(sales):
    log = data.logistics_kpis(sales)
    assert 0 <= log["on_time_rate"] <= 100
    assert log["avg_days_to_ship"] >= 0
    assert log["total_shipped"] == len(sales)


def test_subcategory_profitability(sales):
    sub = data.subcategory_profitability(sales)
    assert not sub.empty
    assert "margin" in sub.columns
    assert "profit" in sub.columns
    assert (sub["revenue"] >= 0).all()
