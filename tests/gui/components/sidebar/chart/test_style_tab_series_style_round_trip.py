"""Tests for StyleTab.load_series_style()/apply_series_style_to()'s
round trip through DataSeries.style, replacing the pre-Phase-3c direct
flat-field reads/writes. Covers the 4 non-vector types' shared path plus
vector's separate branch, and the "match line color" "" -sentinel
convention that must survive the .style migration unchanged.
"""
import sys

from PySide6.QtWidgets import QApplication

from pandaplot.gui.components.sidebar.chart.tabs.style_tab import StyleTab
from pandaplot.models.chart.chart_type import ChartType
from pandaplot.models.chart.series_type import SeriesType
from pandaplot.models.project.items.chart import DataSeries


def _qapp():
    return QApplication.instance() or QApplication(sys.argv)


def _line_series(**overrides):
    defaults = dict(dataset_id="ds1", x_column="x", y_column="y", series_type=SeriesType.LINE)
    defaults.update(overrides)
    return DataSeries(**defaults)


def _vector_series(**overrides):
    defaults = dict(dataset_id="ds1", x_column="x", y_column="y", series_type=SeriesType.VECTOR)
    defaults.update(overrides)
    return DataSeries(**defaults)


def test_load_then_apply_round_trips_line_series_color_and_line_style():
    _qapp()
    tab = StyleTab(app_context=None)
    tab.set_chart_type(ChartType.LINE)
    series = _line_series(color="#112233", line_style="dashed", line_width=3.0)

    tab.load_series_style(series)

    assert tab.line_color_row.currentColor() == "#112233"
    assert tab.line_width_slider.value() == 3.0

    tab.apply_series_style_to(series)

    assert series.style.color == "#112233"
    assert series.style.line_style == "dashed"
    assert series.style.line_width == 3.0


def test_load_then_apply_round_trips_marker_match_line_sentinel():
    """marker_color == "" (the "match line color" convention) must survive
    a load-then-apply cycle unchanged when the toggle isn't touched."""
    _qapp()
    tab = StyleTab(app_context=None)
    tab.set_chart_type(ChartType.LINE)
    series = _line_series(color="#445566", marker_style="circle", marker_color="")

    tab.load_series_style(series)

    assert tab.marker_match_line_toggle.isChecked() is True
    assert tab.marker_color_row.currentColor() == "#445566"  # shows the inherited color

    tab.apply_series_style_to(series)

    assert series.style.marker_color == ""  # still the sentinel, not "#445566"


def test_load_then_apply_round_trips_fill_fields_for_line_series():
    _qapp()
    tab = StyleTab(app_context=None)
    tab.set_chart_type(ChartType.LINE)
    series = _line_series(color="#112233", fill_enabled=True, fill_color="#778899",
                           fill_alpha=0.5, fill_orientation="horizontal", fill_base=1.0,
                           fill_to_index=-1)

    tab.load_series_style(series)

    assert tab.fill_enabled_toggle.isChecked() is True
    assert tab.fill_horizontal_toggle.isChecked() is True

    tab.apply_series_style_to(series)

    assert series.style.fill_enabled is True
    assert series.style.fill_color == "#778899"
    assert series.style.fill_alpha == 0.5
    assert series.style.fill_orientation == "horizontal"


def test_load_then_apply_round_trips_vector_series():
    _qapp()
    tab = StyleTab(app_context=None)
    tab.set_chart_type(ChartType.VECTOR)
    series = _vector_series(vector_color="#abcdef", vector_scale=2.0, vector_width=0.02)

    tab.load_series_style(series)

    assert tab.vector_color_row.currentColor() == "#abcdef"
    assert tab.vector_scale_slider.value() == 2.0

    tab.apply_series_style_to(series)

    assert series.style.vector_color == "#abcdef"
    assert series.style.vector_scale == 2.0
    assert series.style.vector_width == 0.02


def test_load_does_not_crash_for_bar_series_with_no_marker_or_fill_fields():
    """A BarSeriesStyle has no marker_*/fill_* fields at all -- loading
    must not raise AttributeError just because the (hidden) Marker/Fill
    cards' controls still get populated with some default value."""
    _qapp()
    tab = StyleTab(app_context=None)
    tab.set_chart_type(ChartType.BAR)
    series = _line_series(series_type=SeriesType.BAR, color="#654321")

    tab.load_series_style(series)  # must not raise

    assert tab.line_color_row.currentColor() == "#654321"


def test_apply_does_not_write_marker_fields_onto_a_bar_series_style():
    """apply_series_style_to must not attempt to set marker_style/etc. on
    a BarSeriesStyle instance, which doesn't declare those fields."""
    _qapp()
    tab = StyleTab(app_context=None)
    tab.set_chart_type(ChartType.BAR)
    series = _line_series(series_type=SeriesType.BAR, color="#654321")

    tab.apply_series_style_to(series)  # must not raise

    assert series.style.color is not None  # color is still written
    assert not hasattr(series.style, "marker_style")


def test_error_bar_fields_stay_on_dataseries_not_style():
    _qapp()
    tab = StyleTab(app_context=None)
    tab.set_chart_type(ChartType.LINE)
    series = _line_series(color="#112233")

    tab.load_series_style(series)
    tab.apply_series_style_to(series)

    assert not hasattr(series.style, "error_color")
    assert series.error_color == ""  # unchanged default, still a top-level field
