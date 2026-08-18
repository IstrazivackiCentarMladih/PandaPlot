"""Regression test: the Style tab must expose a Confidence Band card
(enable toggle/color/opacity) for a selected fit-data entry, visible only
for "fit" targets, reading/writing `FitData.style.band_*` fields.
"""
import sys

import numpy as np
from PySide6.QtWidgets import QApplication

from pandaplot.app import build_app_context
from pandaplot.gui.components.sidebar.chart.tabs.style_tab import StyleTab
from pandaplot.models.chart.fit_style import FitStyle
from pandaplot.models.chart.series_style import LineSeriesStyle
from pandaplot.models.project.items.chart import DataSeries, FitData


def _qapp():
    return QApplication.instance() or QApplication(sys.argv)


def _fit(**style_kwargs):
    return FitData(
        source_dataset_id="ds1",
        fit_type="linear",
        x_data=np.array([1.0, 2.0]),
        y_data=np.array([1.0, 2.0]),
        label="Fit",
        style=FitStyle(**style_kwargs),
    )


def _series():
    return DataSeries(
        dataset_id="ds1",
        x_column="x",
        y_column="y",
        label="Series",
        style=LineSeriesStyle(),
    )


def test_band_card_visible_only_for_fit_target():
    _qapp()
    app_context = build_app_context()
    style_tab = StyleTab(app_context=app_context)
    style_tab.show()

    style_tab.set_selected("fit", _fit())
    assert style_tab.band_card.isVisible() is True

    style_tab.set_selected("series", _series())
    assert style_tab.band_card.isVisible() is False


def test_load_fit_style_populates_band_controls_from_fitstyle():
    _qapp()
    app_context = build_app_context()
    style_tab = StyleTab(app_context=app_context)

    fit = _fit(band_fill_enabled=False, band_fill_alpha=0.4, band_color="#112233")

    style_tab.load_fit_style(fit)

    assert style_tab.band_enabled_toggle.isChecked() is False
    assert style_tab.band_opacity_slider.value() == 0.4
    assert style_tab.band_color_row.currentColor() == "#112233"


def test_apply_fit_style_to_writes_band_fields():
    _qapp()
    app_context = build_app_context()
    style_tab = StyleTab(app_context=app_context)

    fit = _fit()
    style_tab.load_fit_style(fit)
    style_tab.band_enabled_toggle.setChecked(False)
    style_tab.band_opacity_slider.setValue(0.5)
    style_tab.band_color_row.setCurrentColor("#445566")

    style_tab.apply_fit_style_to(fit)

    assert fit.style.band_fill_enabled is False
    assert fit.style.band_fill_alpha == 0.5
    assert fit.style.band_color == "#445566"
