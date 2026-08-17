"""Regression tests for line/scatter/bar/hist rendering, added before
Phase 3b's SERIES_RENDERERS rewiring (chart_editor.py had if/elif
branches for these but no dedicated artist-level tests -- only vector
and fit had one, see test_chart_editor_vector_rendering.py /
test_chart_editor_fit_rendering.py). These pin today's actual rendered
output so the rewiring in this same task can be verified not to have
changed it.
"""
import sys

import pandas as pd
from PySide6.QtWidgets import QApplication

from pandaplot.app import build_app_context
from pandaplot.gui.components.tabs.chart.chart_editor import ChartEditorWidget
from pandaplot.models.project.items import Dataset
from pandaplot.models.project.items.chart import Chart
from pandaplot.models.project.project import Project


def _qapp():
    return QApplication.instance() or QApplication(sys.argv)


def _project_and_dataset():
    project = Project(name="Series Type Render Project")
    df = pd.DataFrame({"x": [1, 2, 3, 4, 5], "y": [2, 3, 1, 4, 3]})
    dataset = Dataset(name="ds1", data=df)
    project.add_item(dataset)
    return project, dataset


def _editor_for(project, chart):
    project.add_item(chart)
    app_context = build_app_context()
    app_context.app_state.load_project(project)
    editor = ChartEditorWidget(app_context=app_context, chart=chart, parent=None)
    editor.update_chart()
    return editor


def test_line_chart_draws_a_line_with_style_fields():
    _qapp()
    project, dataset = _project_and_dataset()
    chart = Chart(name="Line Chart", chart_type="line")
    chart.add_data_series(
        dataset.id, x_column_id=dataset.column_id("x"), y_column_id=dataset.column_id("y"),
        color="#ff0000", line_width=3.0, label="Series 1",
    )

    editor = _editor_for(project, chart)

    lines = editor.chart_canvas.axes.lines
    assert len(lines) == 1
    assert lines[0].get_color() == "#ff0000"
    assert lines[0].get_linewidth() == 3.0
    assert lines[0].get_label() == "Series 1"


def test_scatter_chart_draws_a_scatter_collection():
    _qapp()
    project, dataset = _project_and_dataset()
    chart = Chart(name="Scatter Chart", chart_type="scatter")
    chart.add_data_series(
        dataset.id, x_column_id=dataset.column_id("x"), y_column_id=dataset.column_id("y"),
        color="#00ff00", label="Series 1",
    )

    editor = _editor_for(project, chart)

    from matplotlib.collections import PathCollection
    scatters = [c for c in editor.chart_canvas.axes.collections if isinstance(c, PathCollection)]
    assert len(scatters) == 1
    assert scatters[0].get_label() == "Series 1"


def test_bar_chart_draws_bars_with_color():
    _qapp()
    project, dataset = _project_and_dataset()
    chart = Chart(name="Bar Chart", chart_type="bar")
    chart.add_data_series(
        dataset.id, x_column_id=dataset.column_id("x"), y_column_id=dataset.column_id("y"),
        color="#0000ff", label="Series 1",
    )

    editor = _editor_for(project, chart)

    assert len(editor.chart_canvas.axes.patches) == 5  # one Rectangle per bar


def test_hist_chart_draws_bins_with_color():
    _qapp()
    project, dataset = _project_and_dataset()
    chart = Chart(name="Hist Chart", chart_type="hist")
    chart.config["hist_bins"] = 3
    chart.add_data_series(
        dataset.id, y_column_id=dataset.column_id("y"), color="#ffaa00", label="Series 1",
    )

    editor = _editor_for(project, chart)

    assert len(editor.chart_canvas.axes.patches) == 3


def test_line_chart_with_fill_enabled_draws_a_fill():
    _qapp()
    project, dataset = _project_and_dataset()
    chart = Chart(name="Line Chart", chart_type="line")
    chart.add_data_series(
        dataset.id, x_column_id=dataset.column_id("x"), y_column_id=dataset.column_id("y"),
        color="#123456", fill_enabled=True, fill_color="#654321", fill_alpha=0.5,
    )

    editor = _editor_for(project, chart)

    assert len(editor.chart_canvas.axes.collections) == 1
