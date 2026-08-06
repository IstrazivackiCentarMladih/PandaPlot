"""Widget-level rendering tests for the colormap/heatmap chart types: the
color-mapped collections are actually drawn, a colorbar is added, and it is
removed (not accumulated) when re-rendering or switching chart type.
"""
import sys

import pandas as pd
from matplotlib.collections import QuadMesh
from PySide6.QtWidgets import QApplication

from pandaplot.app import build_app_context
from pandaplot.gui.components.tabs.chart.chart_editor import ChartEditorWidget
from pandaplot.models.project.items import Dataset
from pandaplot.models.project.items.chart import Chart
from pandaplot.models.project.project import Project


def _qapp():
    return QApplication.instance() or QApplication(sys.argv)


def _editor_with_grid_chart(chart_type):
    app_context = build_app_context()
    project = Project(name="Color Render Project")
    # A regular 2x2 grid so both scatter and pcolormesh have valid data.
    df = pd.DataFrame({
        "x": [0, 1, 0, 1],
        "y": [0, 0, 1, 1],
        "z": [10, 20, 30, 40],
    })
    dataset = Dataset(name="ds1", data=df)
    project.add_item(dataset)
    app_context.app_state.load_project(project)

    chart = Chart(name="Color Chart", chart_type=chart_type)
    chart.add_data_series(
        dataset.id,
        x_column_id=dataset.column_id("x"),
        y_column_id=dataset.column_id("y"),
        z_column_id=dataset.column_id("z"),
        label="S",
    )
    project.add_item(chart)
    editor = ChartEditorWidget(app_context=app_context, chart=chart, parent=None)
    return editor


def _colorbar_axes_count(editor):
    # The main axes plus its twin(s) aside, a colorbar adds an extra Axes to
    # the figure; count figure axes beyond the primary as a proxy.
    return len(editor.chart_canvas.fig.axes)


def test_colormap_scatter_is_drawn_with_colorbar():
    _qapp()
    editor = _editor_with_grid_chart("colormap")
    editor.update_chart()

    assert editor.chart_canvas.axes.collections, "expected a scatter collection"
    assert editor._colorbar is not None
    assert editor.update_status  # sanity: widget intact


def test_heatmap_pcolormesh_is_drawn_with_colorbar():
    _qapp()
    editor = _editor_with_grid_chart("heatmap")
    editor.update_chart()

    meshes = [c for c in editor.chart_canvas.axes.collections if isinstance(c, QuadMesh)]
    assert meshes, "expected a pcolormesh QuadMesh"
    assert editor._colorbar is not None


def test_colorbar_is_not_accumulated_across_rerenders():
    _qapp()
    editor = _editor_with_grid_chart("heatmap")
    editor.update_chart()
    axes_after_first = _colorbar_axes_count(editor)
    editor.update_chart()
    editor.update_chart()
    assert _colorbar_axes_count(editor) == axes_after_first, (
        "re-rendering a heatmap should not stack extra colorbar axes")


def test_switching_away_from_heatmap_removes_colorbar():
    _qapp()
    editor = _editor_with_grid_chart("heatmap")
    editor.update_chart()
    assert editor._colorbar is not None

    editor.chart.chart_type = "scatter"
    editor.update_chart()
    assert editor._colorbar is None
    # Only the primary axes remains (no leftover colorbar axes).
    assert _colorbar_axes_count(editor) == 1


def test_missing_z_column_skips_series_without_crashing():
    _qapp()
    editor = _editor_with_grid_chart("colormap")
    editor.chart.data_series[0].z_column_id = ""
    editor.chart.data_series[0].z_column = ""
    editor.update_chart()
    # No colorbar, no scatter collection, and the status reports the skip.
    assert editor._colorbar is None
