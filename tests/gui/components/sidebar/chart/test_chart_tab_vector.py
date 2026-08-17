"""Tests for ChartTab's Vector chart-type support."""
import sys

import pytest
from PySide6.QtWidgets import QApplication

from pandaplot.gui.components.sidebar.chart.tabs.chart_tab import ChartTab
from pandaplot.models.chart.chart_type import ChartType
from pandaplot.models.chart.series_type import SeriesType
from pandaplot.models.project.items.chart import Chart


@pytest.fixture(scope="module", autouse=True)
def qapp():
    yield QApplication.instance() or QApplication(sys.argv)


def test_loading_a_vector_chart_selects_the_vector_combo_entry():
    tab = ChartTab()
    chart = Chart(name="Vec", chart_type="vector")

    tab.load(chart)

    assert tab.chart_type_control.currentValue() == ChartType.VECTOR


def test_selecting_vector_in_the_combo_sets_the_chart_type():
    tab = ChartTab()
    chart = Chart(name="Vec", chart_type="line")
    tab.load(chart)

    tab.chart_type_control.setCurrentValue(ChartType.VECTOR)
    tab._on_chart_type_index_changed()

    assert chart.chart_type == "vector"


def test_apply_to_writes_back_vector_chart_type():
    tab = ChartTab()
    chart = Chart(name="Vec", chart_type="line")
    tab.load(chart)
    tab.chart_type_control.setCurrentValue(ChartType.VECTOR)

    other_chart = Chart(name="Other", chart_type="line")
    tab.apply_to(other_chart)

    assert other_chart.chart_type == "vector"


def test_chart_type_change_retypes_the_model_before_chart_type_changed_fires():
    """Regression test: chartTypeChanged listeners (style_tab, data_tab)
    must see the chart already retyped -- not the stale pre-switch state
    -- or per-series UI built on top of it (Phase 4c) reads wrong data."""
    chart = Chart(name="C", chart_type="scatter")
    chart.add_data_series(dataset_id="ds1", x_column_id="x", y_column_id="y")

    tab = ChartTab()
    tab.load(chart)

    seen_series_type = []
    tab.chartTypeChanged.connect(
        lambda _value: seen_series_type.append(chart.data_series[0].series_type)
    )

    tab.chart_type_control.setCurrentValue(ChartType.VECTOR)
    tab._on_chart_type_index_changed()

    assert seen_series_type == [SeriesType.VECTOR]
