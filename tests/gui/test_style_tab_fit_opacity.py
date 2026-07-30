"""Regression test: the Style tab's opacity slider must actually apply to a
selected fit-data entry.

Before this fix, `FitData` had no `alpha` field at all: `load_fit_style`
hardcoded the opacity slider to 1.0 on every load, `apply_fit_style_to` never
wrote it back, and chart_editor.py hardcoded `alpha=1.0` when plotting the
fit line -- so moving the opacity slider for a fit had no effect whatsoever.
"""
import sys

import numpy as np
from PySide6.QtWidgets import QApplication

from pandaplot.app import build_app_context
from pandaplot.gui.components.sidebar.chart.tabs.style_tab import StyleTab
from pandaplot.models.project.items.chart import FitData


def _qapp():
    return QApplication.instance() or QApplication(sys.argv)


def _fit(**kwargs):
    return FitData(
        source_dataset_id="ds1",
        fit_type="linear",
        x_data=np.array([1.0, 2.0]),
        y_data=np.array([1.0, 2.0]),
        label="Fit",
        **kwargs,
    )


def test_load_fit_style_reflects_fit_alpha():
    _qapp()
    app_context = build_app_context()
    style_tab = StyleTab(app_context=app_context)

    fit = _fit(alpha=0.4)
    style_tab.load_fit_style(fit)

    assert style_tab.line_opacity_slider.value() == 0.4


def test_apply_fit_style_persists_opacity_slider_to_alpha():
    _qapp()
    app_context = build_app_context()
    style_tab = StyleTab(app_context=app_context)

    fit = _fit(alpha=1.0)
    style_tab.load_fit_style(fit)
    style_tab.line_opacity_slider.setValue(0.3)

    style_tab.apply_fit_style_to(fit)

    assert fit.alpha == 0.3
