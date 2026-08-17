"""Regression test: on a Scatter chart, selecting a fit-data entry in the
Style tab must still show the Line card (a fit is always rendered as a line,
regardless of chart type) and must hide the Marker card (fit data has no
marker concept at all).
"""
import sys

import numpy as np
from PySide6.QtWidgets import QApplication

from pandaplot.app import build_app_context
from pandaplot.gui.components.sidebar.chart.tabs.style_tab import StyleTab
from pandaplot.models.chart.chart_type import ChartType
from pandaplot.models.project.items.chart import DataSeries, FitData


def _qapp():
    return QApplication.instance() or QApplication(sys.argv)


def test_fit_line_card_visible_on_scatter_chart():
    _qapp()
    app_context = build_app_context()
    style_tab = StyleTab(app_context=app_context)
    style_tab.show()
    style_tab.set_chart_type(ChartType.SCATTER)

    fit = FitData(
        source_dataset_id="ds1",
        source_x_column="x",
        source_y_column="y",
        fit_type="linear",
        x_data=np.array([1.0, 2.0]),
        y_data=np.array([1.0, 2.0]),
        label="Fit",
    )
    style_tab.set_selected("fit", fit)

    assert style_tab.line_card.isVisible()
    assert not style_tab.marker_card.isVisible()


def test_series_line_card_hidden_on_scatter_chart():
    _qapp()
    app_context = build_app_context()
    style_tab = StyleTab(app_context=app_context)
    style_tab.show()
    style_tab.set_chart_type(ChartType.SCATTER)

    series = DataSeries(dataset_id="ds1", x_column="x", y_column="y", label="Series A")
    style_tab.set_selected("series", series)

    assert not style_tab.line_card.isVisible()
    assert style_tab.marker_card.isVisible()


def test_fit_line_card_visible_on_line_chart():
    _qapp()
    app_context = build_app_context()
    style_tab = StyleTab(app_context=app_context)
    style_tab.show()
    style_tab.set_chart_type(ChartType.LINE)

    fit = FitData(
        source_dataset_id="ds1",
        source_x_column="x",
        source_y_column="y",
        fit_type="linear",
        x_data=np.array([1.0, 2.0]),
        y_data=np.array([1.0, 2.0]),
        label="Fit",
    )
    style_tab.set_selected("fit", fit)

    assert style_tab.line_card.isVisible()
    assert not style_tab.marker_card.isVisible()


def test_match_line_toggle_hidden_for_scatter_series():
    """A scatter-chart series has no drawn line at all (see above), so
    "Match line" is meaningless: it must be hidden and the marker color
    pickers must always be shown, regardless of the toggle's stored state."""
    _qapp()
    app_context = build_app_context()
    style_tab = StyleTab(app_context=app_context)
    style_tab.show()
    style_tab.set_chart_type(ChartType.SCATTER)

    series = DataSeries(
        dataset_id="ds1", x_column="x", y_column="y", label="Series A",
        marker_color="",  # "" == inherit, i.e. "match line" was on
    )
    style_tab.set_selected("series", series)

    assert not style_tab.marker_match_line_label.isVisible()
    assert not style_tab.marker_match_line_toggle.isVisible()
    assert style_tab.marker_color_row.isVisible()
    assert style_tab.marker_edge_color_row.isVisible()


def test_match_line_toggle_visible_for_line_chart_series():
    _qapp()
    app_context = build_app_context()
    style_tab = StyleTab(app_context=app_context)
    style_tab.show()
    style_tab.set_chart_type(ChartType.LINE)

    series = DataSeries(dataset_id="ds1", x_column="x", y_column="y", label="Series A")
    style_tab.set_selected("series", series)

    assert style_tab.marker_match_line_label.isVisible()
    assert style_tab.marker_match_line_toggle.isVisible()


def test_scatter_series_marker_color_applied_explicitly_even_when_match_line_checked():
    """apply_series_style_to must not persist an inherited ("") marker color
    for a scatter series even if the (now-hidden) toggle is still checked --
    there's no visible line color for it to inherit from."""
    _qapp()
    app_context = build_app_context()
    style_tab = StyleTab(app_context=app_context)
    style_tab.show()
    style_tab.set_chart_type(ChartType.SCATTER)

    series = DataSeries(
        dataset_id="ds1", x_column="x", y_column="y", label="Series A",
        color="#123456", marker_color="",
    )
    style_tab.set_selected("series", series)
    assert style_tab.marker_match_line_toggle.isChecked()  # stored state preserved

    style_tab.apply_series_style_to(series)

    assert series.marker_color == "#123456"
