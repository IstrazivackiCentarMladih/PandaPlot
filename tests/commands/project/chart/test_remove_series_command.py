"""Tests for RemoveSeriesCommand."""
from unittest.mock import Mock

import pytest

from pandaplot.commands.project.chart.remove_series_command import RemoveSeriesCommand
from pandaplot.models.chart.series_style.line import LineSeriesStyle
from pandaplot.models.chart.series_type import SeriesType
from pandaplot.models.project.items.chart import Chart, DataSeries


@pytest.fixture
def app_context_with_chart():
    chart = Chart(name="Test Chart", chart_type="line")

    project = Mock()
    project.find_item.return_value = chart

    app_state = Mock()
    app_state.has_project = True
    app_state.current_project = project

    app_context = Mock()
    app_context.get_app_state.return_value = app_state
    app_context.event_bus = Mock()
    return app_context, chart


def test_undo_restores_series_with_style_as_dataclass_instance(app_context_with_chart):
    """Regression test: execute() captures a series via copy.deepcopy(),
    which preserves series.style as a typed dataclass instance (unlike the
    old asdict()-then-reconstruct path, which flattened style into a plain
    dict on the way out). undo() must restore that same typed instance. A
    plain-dict `.style` would blow up the next Chart.to_dict() call, since
    it does dataclasses.asdict(series.style)."""
    app_context, chart = app_context_with_chart
    chart.data_series.append(
        DataSeries(
            dataset_id="ds1",
            x_column="x",
            y_column="y",
            series_type=SeriesType.LINE,
            style=LineSeriesStyle(color="#112233"),
        )
    )

    command = RemoveSeriesCommand(app_context, chart_id=chart.id, series_index=0)
    assert command.execute() is True
    assert len(chart.data_series) == 0

    command.undo()
    assert len(chart.data_series) == 1

    restored = chart.data_series[0]
    assert isinstance(restored.style, LineSeriesStyle)
    assert restored.style.color == "#112233"

    # Must not raise -- this is the exact crash the bug report describes:
    # execute -> undo -> to_dict (e.g. on save).
    data = chart.to_dict()
    assert data["data_series"][0]["style"]["color"] == "#112233"


def test_redo_after_undo_removes_series_again(app_context_with_chart):
    app_context, chart = app_context_with_chart
    chart.data_series.append(
        DataSeries(
            dataset_id="ds1",
            x_column="x",
            y_column="y",
            series_type=SeriesType.LINE,
            style=LineSeriesStyle(),
        )
    )

    command = RemoveSeriesCommand(app_context, chart_id=chart.id, series_index=0)
    command.execute()
    command.undo()
    command.redo()
    assert len(chart.data_series) == 0
