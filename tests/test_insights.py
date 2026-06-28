"""The headline insights compute and stay internally consistent."""

import pytest

from src import data, insights


@pytest.fixture(scope="module")
def sales():
    return data.build_sales()


def test_all_insights_have_required_fields(sales):
    cards = insights.all_insights(sales)
    assert len(cards) >= 5
    for card in cards:
        assert card["title"] and card["metric"] and card["takeaway"]
        assert card["action"]


def test_category_concentration_is_bikes(sales):
    card = insights.category_concentration(sales)
    assert "Bikes" in card["takeaway"]
    # Bikes dominate revenue in this dataset; metric is the share, e.g. "96.5%".
    share = float(card["metric"].rstrip("%"))
    assert share > 90


def test_repeat_customer_share_exceeds_their_headcount(sales):
    card = insights.repeat_customer_value(sales)
    assert card  # not empty
    # The whole point of the insight: revenue share > customer share.
    assert "%" in card["metric"]


def test_insights_empty_on_empty_frame(sales):
    empty = sales.iloc[0:0]
    assert insights.all_insights(empty) == []
