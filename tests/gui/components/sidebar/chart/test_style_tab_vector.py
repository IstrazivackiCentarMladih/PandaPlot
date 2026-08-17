"""Tests for StyleTab's Vector chart-type support."""
import sys

import pytest
from PySide6.QtWidgets import QApplication

from pandaplot.gui.components.sidebar.chart.tabs.style_tab import StyleTab
from pandaplot.models.chart.chart_type import ChartType
from pandaplot.models.chart.series_style import VectorSeriesStyle
from pandaplot.models.chart.series_type import SeriesType
from pandaplot.models.project.items.chart import DataSeries


@pytest.fixture(scope="module", autouse=True)
def qapp():
    yield QApplication.instance() or QApplication(sys.argv)


def _tab():
    # Qt only reports isVisible() truthfully for a widget whose top-level
    # ancestor has actually been shown (see tests/gui/test_style_tab_*
    # visibility tests for the same pattern) -- without this, isVisible()
    # is always False regardless of setVisible() calls.
    tab = StyleTab(app_context=None)
    tab.show()
    return tab


def test_vector_card_is_shown_only_for_a_vector_series_target():
    tab = _tab()
    series = DataSeries(dataset_id="ds1")
    tab.set_chart_type(ChartType.VECTOR)
    tab.set_selected("series", series)

    assert tab.vector_card.isVisible() is True
    assert tab.line_card.isVisible() is False
    assert tab.marker_card.isVisible() is False
    assert tab.fill_card.isVisible() is False
    assert tab.error_bars_card.isVisible() is False


def test_vector_card_is_hidden_for_a_line_series_target():
    tab = _tab()
    series = DataSeries(dataset_id="ds1")
    tab.set_chart_type(ChartType.LINE)
    tab.set_selected("series", series)

    assert tab.vector_card.isVisible() is False


def test_apply_series_style_to_writes_vector_fields():
    tab = _tab()
    series = DataSeries(dataset_id="ds1", series_type=SeriesType.VECTOR)
    tab.set_chart_type(ChartType.VECTOR)
    tab.set_selected("series", series)

    tab.vector_color_row.setCurrentColor("#123456")
    tab.vector_scale_slider.setValue(3.0)
    tab.vector_width_slider.setValue(0.02)
    tab.vector_head_width_slider.setValue(4.0)
    tab.vector_head_length_slider.setValue(7.0)
    tab.vector_head_axis_length_slider.setValue(6.0)
    tab.vector_colormap_control.setCurrentValue("plasma")

    tab.apply_series_style_to(series)

    assert series.style.vector_color == "#123456"
    assert series.style.vector_scale == 3.0
    assert series.style.vector_width == 0.02
    assert series.style.vector_head_width == 4.0
    assert series.style.vector_head_length == 7.0
    assert series.style.vector_head_axis_length == 6.0
    assert series.style.vector_colormap == "plasma"


def test_load_series_style_populates_vector_card_from_series():
    tab = _tab()
    series = DataSeries(
        dataset_id="ds1", series_type=SeriesType.VECTOR,
        style=VectorSeriesStyle(
            vector_color="#abcdef", vector_scale=2.0, vector_width=0.03,
            vector_head_width=5.0, vector_head_length=8.0, vector_head_axis_length=7.0,
            vector_colormap="cool",
        ),
    )
    tab.set_chart_type(ChartType.VECTOR)

    tab.load_series_style(series)

    assert tab.vector_color_row.currentColor() == "#abcdef"
    assert tab.vector_scale_slider.value() == 2.0
    assert tab.vector_width_slider.value() == 0.03
    assert tab.vector_head_width_slider.value() == 5.0
    assert tab.vector_head_length_slider.value() == 8.0
    assert tab.vector_head_axis_length_slider.value() == 7.0
    assert tab.vector_colormap_control.currentValue() == "cool"
