"""Regression test: a single fit-data entry must draw exactly one curve.

A botched merge (PR #59, "multiple y axis") left both the old
unconditional `self.chart_canvas.axes.plot(...)` call and the new
axis-aware `fit_axes.plot(...)` call in ChartEditorWidget.update_chart(),
so every fit was rendered twice.
"""
import sys

import numpy as np
import pandas as pd
from PySide6.QtWidgets import QApplication

from pandaplot.app import build_app_context
from pandaplot.gui.components.tabs.chart.chart_editor import ChartEditorWidget
from pandaplot.models.project.items import Dataset
from pandaplot.models.project.items.chart import Chart
from pandaplot.models.project.project import Project


def _qapp():
    return QApplication.instance() or QApplication(sys.argv)


def _chart_with_one_fit(project, dataset):
    chart = Chart(name="Fit Chart", chart_type="scatter")
    chart.add_data_series(dataset.id, "x", "y", label="Series A")
    chart.add_fit_data(
        source_dataset_id=dataset.id,
        source_x_column="x",
        source_y_column="y",
        fit_type="linear",
        x_data=np.array([1.0, 2.0, 3.0]),
        y_data=np.array([1.0, 2.0, 3.0]),
        label="Linear Fit",
        color="#ff0000",
    )
    project.add_item(chart)
    return chart


def test_one_fit_draws_exactly_one_line_on_primary_axis():
    _qapp()
    app_context = build_app_context()
    project = Project(name="Fit Render Project")
    df = pd.DataFrame({"x": [1, 2, 3], "y": [1, 4, 9]})
    dataset = Dataset(name="ds1", data=df)
    project.add_item(dataset)
    app_context.app_state.load_project(project)

    chart = _chart_with_one_fit(project, dataset)
    editor = ChartEditorWidget(app_context=app_context, chart=chart, parent=None)
    editor.update_chart()

    fit_lines = [line for line in editor.chart_canvas.axes.get_lines() if line.get_color() == "#ff0000"]
    assert len(fit_lines) == 1, f"expected 1 line for the fit, got {len(fit_lines)}"


def test_confidence_band_for_a_secondary_axis_fit_is_drawn_on_that_axis():
    _qapp()
    app_context = build_app_context()
    project = Project(name="Fit Render Project 2")
    df = pd.DataFrame({"x": [1, 2, 3], "y": [1, 4, 9]})
    dataset = Dataset(name="ds1", data=df)
    project.add_item(dataset)
    app_context.app_state.load_project(project)

    chart = Chart(name="Secondary Fit Chart", chart_type="line")
    chart.add_data_series(dataset.id, "x", "y", label="Series A", y_axis="secondary")
    chart.add_fit_data(
        source_dataset_id=dataset.id,
        source_x_column="x",
        source_y_column="y",
        fit_type="linear",
        x_data=np.array([1.0, 2.0, 3.0]),
        y_data=np.array([1.0, 2.0, 3.0]),
        label="Linear Fit",
        color="#00ff00",
        confidence_lower=np.array([0.5, 1.5, 2.5]),
        confidence_upper=np.array([1.5, 2.5, 3.5]),
    )
    project.add_item(chart)

    editor = ChartEditorWidget(app_context=app_context, chart=chart, parent=None)
    editor.update_chart()

    assert editor.chart_canvas.axes2 is not None, "secondary axis should have been created"
    assert len(editor.chart_canvas.axes2.collections) == 1, (
        "confidence band should be drawn on the secondary axis, not the primary one"
    )
    assert len(editor.chart_canvas.axes.collections) == 0, (
        "confidence band leaked onto the primary axis"
    )
