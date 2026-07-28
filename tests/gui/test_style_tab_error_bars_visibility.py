"""Regression test: the Style tab's Error Bars card must only show for a
selected series that actually has an error-bar column configured -- not for
every series unconditionally.
"""
import sys

from PySide6.QtWidgets import QApplication

from pandaplot.app import build_app_context
from pandaplot.gui.components.sidebar.chart.tabs.style_tab import StyleTab
from pandaplot.models.chart.chart_configuration import ChartType
from pandaplot.models.project.items.chart import DataSeries


def _qapp():
    return QApplication.instance() or QApplication(sys.argv)


def test_error_bars_card_hidden_when_no_error_columns_configured():
    _qapp()
    app_context = build_app_context()
    style_tab = StyleTab(app_context=app_context)
    style_tab.show()
    style_tab.set_chart_type(ChartType.LINE)

    series = DataSeries(dataset_id="ds1", x_column="x", y_column="y", label="Series A")
    style_tab.set_selected("series", series)

    assert not style_tab.error_bars_card.isVisible()


def test_error_bars_card_visible_when_y_error_column_configured():
    _qapp()
    app_context = build_app_context()
    style_tab = StyleTab(app_context=app_context)
    style_tab.show()
    style_tab.set_chart_type(ChartType.LINE)

    series = DataSeries(
        dataset_id="ds1", x_column="x", y_column="y", label="Series A",
        y_error_column_id="err-col-id",
    )
    style_tab.set_selected("series", series)

    assert style_tab.error_bars_card.isVisible()


def test_error_bars_card_hidden_for_fit():
    _qapp()
    app_context = build_app_context()
    style_tab = StyleTab(app_context=app_context)
    style_tab.show()
    style_tab.set_chart_type(ChartType.LINE)

    series = DataSeries(
        dataset_id="ds1", x_column="x", y_column="y", label="Series A",
        y_error_column_id="err-col-id",
    )
    style_tab.set_selected("series", series)
    assert style_tab.error_bars_card.isVisible()

    from pandaplot.models.project.items.chart import FitData
    import numpy as np
    fit = FitData(
        source_dataset_id="ds1", fit_type="linear",
        x_data=np.array([1.0]), y_data=np.array([2.0]), label="Fit",
    )
    style_tab.set_selected("fit", fit)

    assert not style_tab.error_bars_card.isVisible()
