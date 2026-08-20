"""Regression tests for Task 6: ChartEditorWidget's shared colorbar
lifecycle for Colormap/Heatmap series.

Pins the fix for the PR #156 review bug where Figure.colorbar(...,
use_gridspec=True) subdivides the axes' gridspec to make room, and that
subdivision survives colorbar.remove() -- so repeatedly re-rendering a
colormap/heatmap series shrank the plot area on every render. Follows the
same helper-function pattern (not a pytest fixture) as
test_chart_editor_series_type_rendering.py.
"""
import sys

import pandas as pd
from PySide6.QtWidgets import QApplication

from pandaplot.app import build_app_context
from pandaplot.gui.components.tabs.chart.chart_editor import ChartEditorWidget
from pandaplot.models.chart.chart_type import ChartType
from pandaplot.models.chart.series_style import HeatmapSeriesStyle
from pandaplot.models.chart.series_type import SeriesType
from pandaplot.models.project.items import Dataset
from pandaplot.models.project.items.chart import Chart, DataSeries
from pandaplot.models.project.project import Project


def _qapp():
    return QApplication.instance() or QApplication(sys.argv)


def _project_and_dataset():
    project = Project(name="Colormap Render Project")
    df = pd.DataFrame({
        "x": [1, 2, 3, 1, 2, 3],
        "y": [1, 1, 1, 2, 2, 2],
        "z": [0.1, 0.2, 0.3, 0.4, 0.5, 0.6],
    })
    dataset = Dataset(name="ds1", data=df)
    project.add_item(dataset)
    return project, dataset


def _editor_for(project, chart):
    project.add_item(chart)
    app_context = build_app_context()
    app_context.app_state.load_project(project)
    editor = ChartEditorWidget(app_context=app_context, chart=chart, parent=None)
    return editor


def _heatmap_chart(dataset):
    chart = Chart(name="Heatmap Chart", chart_type="line")
    chart.set_chart_type(ChartType.HEATMAP)
    chart.data_series.append(DataSeries(
        dataset_id=dataset.id, x_column_id=dataset.column_id("x"),
        y_column_id=dataset.column_id("y"), series_type=SeriesType.HEATMAP,
        style=HeatmapSeriesStyle(z_column_id=dataset.column_id("z")),
    ))
    return chart


def _line_chart(dataset):
    chart = Chart(name="Line Chart", chart_type="line")
    chart.set_chart_type(ChartType.LINE)
    chart.data_series.append(DataSeries(
        dataset_id=dataset.id, x_column_id=dataset.column_id("x"),
        y_column_id=dataset.column_id("y"), series_type=SeriesType.LINE,
    ))
    return chart


def test_heatmap_render_draws_colorbar_and_does_not_shrink_on_rerender():
    _qapp()
    project, dataset = _project_and_dataset()
    chart = _heatmap_chart(dataset)
    editor = _editor_for(project, chart)

    editor.update_chart()
    assert editor._colorbar is not None
    width_after_first_render = editor.chart_canvas.axes.get_position().bounds[2]

    editor.chart.data_series[0].style.colormap = "plasma"
    editor.update_chart()
    editor.update_chart()
    width_after_third_render = editor.chart_canvas.axes.get_position().bounds[2]

    assert width_after_third_render == width_after_first_render


def test_switching_away_from_heatmap_removes_colorbar():
    _qapp()
    project, dataset = _project_and_dataset()
    chart = _heatmap_chart(dataset)
    editor = _editor_for(project, chart)

    editor.update_chart()
    assert editor._colorbar is not None

    chart.set_chart_type(ChartType.LINE)
    editor.update_chart()
    assert editor._colorbar is None

    # The actual PR #156 review bug was the plot area shrinking, not merely
    # a stale colorbar reference -- a regression that keeps the colorbar
    # teardown working but drops the GridSpec reset would leave the
    # assertion above green while reintroducing the shrinking bug. Prove
    # the axes size is genuinely restored by comparing against a fresh,
    # never-heatmapped Line chart editor's axes width.
    fresh_project, fresh_dataset = _project_and_dataset()
    fresh_chart = _line_chart(fresh_dataset)
    fresh_editor = _editor_for(fresh_project, fresh_chart)
    fresh_editor.update_chart()

    switched_width = editor.chart_canvas.axes.get_position().bounds[2]
    fresh_width = fresh_editor.chart_canvas.axes.get_position().bounds[2]
    assert switched_width == fresh_width


def test_heatmap_rerender_does_not_log_stale_colorbar_removal_failure(caplog):
    """colorbar.remove() must succeed while its mappable's axes still exist
    (i.e. before axes.clear()), so the debug log for a failed removal
    should never fire during normal heatmap re-renders."""
    _qapp()
    project, dataset = _project_and_dataset()
    chart = _heatmap_chart(dataset)
    editor = _editor_for(project, chart)

    with caplog.at_level("DEBUG"):
        editor.update_chart()
        editor.update_chart()
        editor.update_chart()

    assert "Failed to remove stale colorbar" not in caplog.text


def test_colorbar_show_false_skips_the_shared_colorbar():
    """A series with colorbar_show=False must not contribute to the shared
    colorbar -- proving the gate reads style.colorbar_show, not merely
    whether the renderer returned a mappable."""
    _qapp()
    project, dataset = _project_and_dataset()
    chart = _heatmap_chart(dataset)
    chart.data_series[0].style.colorbar_show = False
    editor = _editor_for(project, chart)

    editor.update_chart()

    assert editor._colorbar is None


def test_only_one_colorbar_drawn_for_multiple_colorbar_series():
    """Two colorbar-enabled Heatmap series on one chart must still result
    in exactly one shared colorbar, attached to the first one's mappable."""
    _qapp()
    project, dataset = _project_and_dataset()
    chart = _heatmap_chart(dataset)
    chart.data_series.append(DataSeries(
        dataset_id=dataset.id, x_column_id=dataset.column_id("x"),
        y_column_id=dataset.column_id("y"), series_type=SeriesType.HEATMAP,
        style=HeatmapSeriesStyle(z_column_id=dataset.column_id("z")),
    ))
    editor = _editor_for(project, chart)

    editor.update_chart()

    assert editor._colorbar is not None
    assert len(editor.chart_canvas.fig.axes) == 2  # main axes + 1 colorbar axes
