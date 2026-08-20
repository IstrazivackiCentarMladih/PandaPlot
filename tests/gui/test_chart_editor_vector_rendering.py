"""Tests for rendering a vector (quiver) chart type."""
import sys

import pandas as pd
from matplotlib.quiver import Quiver
from PySide6.QtWidgets import QApplication

from pandaplot.app import build_app_context
from pandaplot.gui.components.tabs.chart.chart_editor import ChartEditorWidget
from pandaplot.models.chart.series_style import VectorSeriesStyle
from pandaplot.models.project.items import Dataset
from pandaplot.models.project.items.chart import Chart
from pandaplot.models.project.project import Project


def _qapp():
    return QApplication.instance() or QApplication(sys.argv)


def _project_and_dataset():
    project = Project(name="Vector Render Project")
    df = pd.DataFrame({
        "x": [0, 1, 2], "y": [0, 1, 2], "u": [1.0, 0.5, -1.0], "v": [0.0, 1.0, 0.5],
        "mag": [1.0, 1.1, 1.5],
    })
    dataset = Dataset(name="ds1", data=df)
    project.add_item(dataset)
    return project, dataset


def test_vector_chart_draws_a_quiver_collection():
    _qapp()
    app_context = build_app_context()
    project, dataset = _project_and_dataset()
    app_context.app_state.load_project(project)

    chart = Chart(name="Vector Chart", chart_type="vector")
    chart.add_data_series(
        dataset.id, x_column_id=dataset.column_id("x"), y_column_id=dataset.column_id("y"),
        style=VectorSeriesStyle(
            u_column_id=dataset.column_id("u"), v_column_id=dataset.column_id("v"),
            vector_color="#00ff00"), label="Field",
    )
    project.add_item(chart)

    editor = ChartEditorWidget(app_context=app_context, chart=chart, parent=None)
    editor.update_chart()

    quivers = [c for c in editor.chart_canvas.axes.collections if isinstance(c, Quiver)]
    assert len(quivers) == 1


def test_vector_chart_with_magnitude_column_uses_a_colormap():
    _qapp()
    app_context = build_app_context()
    project, dataset = _project_and_dataset()
    app_context.app_state.load_project(project)

    chart = Chart(name="Vector Chart", chart_type="vector")
    chart.add_data_series(
        dataset.id, x_column_id=dataset.column_id("x"), y_column_id=dataset.column_id("y"),
        style=VectorSeriesStyle(
            u_column_id=dataset.column_id("u"), v_column_id=dataset.column_id("v"),
            magnitude_column_id=dataset.column_id("mag"),
            vector_colormap="plasma"), label="Field",
    )
    project.add_item(chart)

    editor = ChartEditorWidget(app_context=app_context, chart=chart, parent=None)
    editor.update_chart()

    quivers = [c for c in editor.chart_canvas.axes.collections if isinstance(c, Quiver)]
    assert len(quivers) == 1
    assert quivers[0].get_cmap().name == "plasma"


def test_vector_chart_with_magnitude_column_but_solid_colormap_ignores_magnitude():
    """vector_colormap == "" ("Solid color" in the Style tab) must render a
    flat vector_color even when a magnitude column is configured -- the
    magnitude column only drives coloring once the user actually picks a
    colormap, matching the Style tab's "Solid color" label."""
    _qapp()
    app_context = build_app_context()
    project, dataset = _project_and_dataset()
    app_context.app_state.load_project(project)

    chart = Chart(name="Vector Chart", chart_type="vector")
    chart.add_data_series(
        dataset.id, x_column_id=dataset.column_id("x"), y_column_id=dataset.column_id("y"),
        style=VectorSeriesStyle(
            u_column_id=dataset.column_id("u"), v_column_id=dataset.column_id("v"),
            magnitude_column_id=dataset.column_id("mag"),
            vector_colormap="", vector_color="#00ff00"),
        label="Field",
    )
    project.add_item(chart)

    editor = ChartEditorWidget(app_context=app_context, chart=chart, parent=None)
    editor.update_chart()

    quivers = [c for c in editor.chart_canvas.axes.collections if isinstance(c, Quiver)]
    assert len(quivers) == 1
    assert quivers[0].get_facecolor().tolist()[0][:3] == [0.0, 1.0, 0.0]
