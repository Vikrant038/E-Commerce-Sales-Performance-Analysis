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
