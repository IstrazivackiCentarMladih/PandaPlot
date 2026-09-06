"""Tests for chart series selection by clicking on graph artists or legend items."""
import sys
from types import SimpleNamespace
from unittest.mock import MagicMock

import pandas as pd
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from pandaplot.app import build_app_context
from pandaplot.gui.components.sidebar.chart.chart_properties_panel import ChartPropertiesPanel
from pandaplot.gui.components.tabs.chart.chart_editor import ChartEditorWidget
from pandaplot.models.events.event_types import ChartEvents
from pandaplot.models.project.items import Dataset
from pandaplot.models.project.items.chart import Chart
from pandaplot.models.project.project import Project


def _qapp():
    return QApplication.instance() or QApplication(sys.argv)


def _make_project_and_chart():
    project = Project(name="Test Project")
    df = pd.DataFrame({"x": [1, 2, 3], "y1": [4, 5, 6], "y2": [7, 8, 9]})
    dataset = Dataset(name="ds1", data=df)
    project.add_item(dataset)

    chart = Chart(name="Test Chart", chart_type="line")
    chart.add_data_series(dataset.id, x_column="x", y_column="y1", label="Series 1")
    chart.add_data_series(dataset.id, x_column="x", y_column="y2", label="Series 2")
    project.add_item(chart)

    return project, dataset, chart


def test_chart_editor_artist_picking_and_event_publishing():
    _qapp()
    app_ctx = build_app_context()
    project, dataset, chart = _make_project_and_chart()
    app_ctx.app_state.load_project(project)

    widget = ChartEditorWidget(app_context=app_ctx, chart=chart, parent=None)

    # Verify artist series map populated
    assert len(widget._artist_series_map) > 0

    # Pick event listener check
    listener = MagicMock()
    app_ctx.event_bus.subscribe(ChartEvents.SERIES_SELECTED, listener)

    # Pick an artist mapped to series 1 (index 1)
    target_artist = None
    for artist, idx in widget._artist_series_map.items():
        if idx == 1:
            target_artist = artist
            break

    assert target_artist is not None

    # Simulate pick event
    class PickEvent:
        artist = target_artist

    widget._on_pick_event(PickEvent())

    listener.assert_called_once()
    event_data = listener.call_args[0][0]
    assert event_data["chart_id"] == chart.id
    assert event_data["series_index"] == 1


def test_chart_properties_panel_handles_series_selected_event():
    _qapp()
    app_ctx = build_app_context()
    project, dataset, chart = _make_project_and_chart()
    app_ctx.app_state.load_project(project)

    panel = ChartPropertiesPanel(app_context=app_ctx)
    panel.set_project(project)
    panel.load_chart_object(chart)

    # Initial selected index should be 0
    assert panel.data_tab.selected_index == 0

    # Emit ChartEvents.SERIES_SELECTED for series_index=1
    app_ctx.event_bus.emit(
        ChartEvents.SERIES_SELECTED,
        {"chart_id": chart.id, "series_index": 1},
    )

    assert panel.data_tab.selected_index == 1


def test_bar_series_legend_handle_resolves_to_series_index():
    """A bar/hist series' legend entry is a BarContainer, not one of the
    individual bar Patches that `_track_new_artists` maps directly -- the
    legend resolution must recurse into the container to find a tracked
    patch, or clicking that legend entry silently does nothing (#107)."""
    _qapp()
    app_ctx = build_app_context()
    project = Project(name="Test Project")
    df = pd.DataFrame({"x": [1, 2, 3], "y1": [4, 5, 6], "y2": [7, 8, 9]})
    dataset = Dataset(name="ds1", data=df)
    project.add_item(dataset)

    chart = Chart(name="Bar Chart", chart_type="bar")
    chart.add_data_series(dataset.id, x_column="x", y_column="y1", label="Bars 1", series_type="bar")
    chart.add_data_series(dataset.id, x_column="x", y_column="y2", label="Bars 2", series_type="bar")
    project.add_item(chart)
    app_ctx.app_state.load_project(project)

    widget = ChartEditorWidget(app_context=app_ctx, chart=chart, parent=None)

    handles, _ = widget.chart_canvas.axes.get_legend_handles_labels()
    assert handles, "expected at least one legend handle for the bar series"

    resolved = [widget._resolve_series_index_for_handle(h) for h in handles]
    assert resolved == [0, 1]


def test_fit_series_pick_event_resolves_to_offset_index():
    _qapp()
    app_ctx = build_app_context()
    project, dataset, chart = _make_project_and_chart()
    chart.add_fit_data(
        dataset.id, fit_type="linear",
        x_data=pd.array([1, 2, 3]), y_data=pd.array([1, 2, 3]),
        source_x_column_id="x", source_y_column_id="y1", label="Fit 1",
    )
    app_ctx.app_state.load_project(project)

    widget = ChartEditorWidget(app_context=app_ctx, chart=chart, parent=None)

    total_data_series = len(chart.data_series)
    fit_artist = next(
        artist for artist, idx in widget._artist_series_map.items()
        if idx == total_data_series
    )

    listener = MagicMock()
    app_ctx.event_bus.subscribe(ChartEvents.SERIES_SELECTED, listener)
    widget._on_pick_event(SimpleNamespace(artist=fit_artist))

    listener.assert_called_once()
    event_data = listener.call_args[0][0]
    assert event_data["series_index"] == total_data_series


def test_hover_over_pickable_artist_shows_pointing_hand_cursor():
    _qapp()
    app_ctx = build_app_context()
    project, dataset, chart = _make_project_and_chart()
    app_ctx.app_state.load_project(project)

    widget = ChartEditorWidget(app_context=app_ctx, chart=chart, parent=None)

    # Isolate from the real (many-artist) map built by rendering: a fake
    # event lacking real pixel coordinates would blow up any unmocked
    # artist's `.contains()`.
    fake_artist = MagicMock()
    widget._artist_series_map = {fake_artist: 0}

    hit_event = SimpleNamespace(inaxes=widget.chart_canvas.axes)
    fake_artist.contains.return_value = (True, {})
    widget._on_canvas_motion(hit_event)
    assert widget.chart_canvas.cursor().shape() == Qt.CursorShape.PointingHandCursor

    fake_artist.contains.return_value = (False, {})
    widget._on_canvas_motion(hit_event)
    assert widget.chart_canvas.cursor().shape() == Qt.CursorShape.ArrowCursor

    miss_event = SimpleNamespace(inaxes=None)
    widget._on_canvas_motion(miss_event)
    assert widget.chart_canvas.cursor().shape() == Qt.CursorShape.ArrowCursor
