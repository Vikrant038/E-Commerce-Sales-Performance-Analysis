"""Unit tests for all Plotly figure builders in src/charts.py."""

import plotly.graph_objects as go
import pytest

from src import charts, data


@pytest.fixture(scope="module")
def sales():
    return data.build_sales()


@pytest.fixture(scope="module")
def empty_sales(sales):
    return sales.iloc[0:0]


@pytest.mark.parametrize(
    "chart_func",
    [
        charts.monthly_trend,
        charts.yearly_revenue,
        charts.category_donut,
        charts.new_vs_returning,
        charts.seasonality,
        charts.subcategory_bar,
        charts.margin_by_category,
        charts.top_products,
        charts.cost_segmentation,
        charts.segment_split,
        charts.age_groups,
        charts.top_countries,
        charts.choropleth_world_map,
        charts.margin_vs_revenue_scatter,
        charts.product_affinity_bars,
        charts.fulfillment_on_time_gauge,
        charts.shipping_delay_distribution,
        charts.rfm_segment_distribution,
        charts.cohort_retention_heatmap,
    ],
)
def test_charts_render_valid_figure_on_normal_data(sales, chart_func):
    fig = chart_func(sales)
    assert isinstance(fig, go.Figure)


@pytest.mark.parametrize(
    "chart_func",
    [
        charts.monthly_trend,
        charts.yearly_revenue,
        charts.category_donut,
        charts.new_vs_returning,
        charts.seasonality,
        charts.subcategory_bar,
        charts.margin_by_category,
        charts.top_products,
        charts.cost_segmentation,
        charts.segment_split,
        charts.age_groups,
        charts.top_countries,
        charts.choropleth_world_map,
        charts.margin_vs_revenue_scatter,
        charts.product_affinity_bars,
        charts.fulfillment_on_time_gauge,
        charts.shipping_delay_distribution,
        charts.rfm_segment_distribution,
        charts.cohort_retention_heatmap,
    ],
)
def test_charts_handle_empty_dataframe_gracefully(empty_sales, chart_func):
    # None of the chart builders should crash on empty slices
    fig = chart_func(empty_sales)
    assert isinstance(fig, go.Figure)
