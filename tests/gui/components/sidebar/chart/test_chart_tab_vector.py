"""Tests for ChartTab's Vector chart-type support."""
import sys

import pytest
from PySide6.QtWidgets import QApplication

from pandaplot.gui.components.sidebar.chart.tabs.chart_tab import ChartTab
from pandaplot.models.chart.chart_type import ChartType
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
