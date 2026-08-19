"""Tests for ChartTab's chart-type selector."""
import sys

import pytest
from PySide6.QtWidgets import QApplication

from pandaplot.gui.components.sidebar.chart.tabs.chart_tab import ChartTab
from pandaplot.models.chart.chart_type import ChartType
from pandaplot.models.project.items.chart import Chart


@pytest.fixture(scope="module", autouse=True)
def qapp():
    yield QApplication.instance() or QApplication(sys.argv)


def _is_option_enabled(tab: ChartTab, chart_type: ChartType) -> bool:
    combo = tab.chart_type_control
    index = combo.findData(chart_type)
    item = combo.model().item(index)
    return item.isEnabled()


def test_vector_chart_disables_bar_as_a_switch_target():
    """Reported live: "I don't think we should support going from vector
    to barchart" -- the option must be disabled, not just silently
    force-retype on selection."""
    tab = ChartTab()
    chart = Chart(name="Vector Chart", chart_type="vector")
    tab.load(chart)

    assert _is_option_enabled(tab, ChartType.BAR) is False
    assert _is_option_enabled(tab, ChartType.LINE) is True
    assert _is_option_enabled(tab, ChartType.SCATTER) is True
    assert _is_option_enabled(tab, ChartType.VECTOR) is True


def test_scatter_chart_still_allows_switching_to_bar():
    """Existing, preserved case."""
    tab = ChartTab()
    chart = Chart(name="Scatter Chart", chart_type="scatter")
    tab.load(chart)

    assert _is_option_enabled(tab, ChartType.BAR) is True


def test_disabled_option_has_an_explanatory_tooltip():
    tab = ChartTab()
    chart = Chart(name="Vector Chart", chart_type="vector")
    tab.load(chart)

    combo = tab.chart_type_control
    index = combo.findData(ChartType.BAR)
    tooltip = combo.model().item(index).toolTip()
    assert tooltip != ""


def test_compatibility_is_recomputed_after_switching_type():
    """After Vector -> Line, Bar must still reflect Line's own
    compatibility (disabled, since LINE isn't in BAR.allowed_series_types),
    proving the disabled-state check reruns on every type change rather
    than being computed once at load()."""
    tab = ChartTab()
    chart = Chart(name="Vector Chart", chart_type="vector")
    tab.load(chart)

    line_index = tab.chart_type_control.findData(ChartType.LINE)
    tab.chart_type_control.setCurrentIndex(line_index)

    assert _is_option_enabled(tab, ChartType.BAR) is False
    assert _is_option_enabled(tab, ChartType.HIST) is False
