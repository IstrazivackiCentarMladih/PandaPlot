"""Tests for RenameColumnCommand (DataFrame rename + chart-reference cascade)."""

from unittest.mock import Mock

import numpy as np
import pandas as pd
import pytest

from pandaplot.commands.project.dataset.rename_column_command import RenameColumnCommand
from pandaplot.models.events.event_types import ChartEvents, DatasetOperationEvents
from pandaplot.models.project import Project
from pandaplot.models.project.items import Chart, Dataset


@pytest.fixture
def env():
    project = Project("P")
    dataset = Dataset(name="ds", data=pd.DataFrame({"a": [1, 2], "b": [3, 4]}))
    other = Dataset(name="other", data=pd.DataFrame({"a": [5]}))
    project.add_item(dataset)
    project.add_item(other)

    chart = Chart(name="c")
    chart.add_data_series(dataset.id, "a", "b", label="s1")
    chart.add_data_series(other.id, "a", "a", label="s2")  # other dataset: must not change
    chart.add_fit_data(dataset.id, "a", "b", "Linear",
                       np.array([1.0]), np.array([2.0]))
    project.add_item(chart)

    untouched_chart = Chart(name="c2")
    untouched_chart.add_data_series(other.id, "a", "a", label="s3")
    project.add_item(untouched_chart)

    app_state = Mock()
    app_state.has_project = True
    app_state.current_project = project
    app_context = Mock()
    app_context.get_app_state.return_value = app_state
    app_context.get_ui_controller.return_value = Mock()
    app_context.event_bus = Mock()
    return app_context, dataset, other, chart


def _chart_updated_calls(app_context):
    return [c for c in app_context.event_bus.emit.call_args_list
            if c.args[0] == ChartEvents.CHART_UPDATED]


def test_rename_updates_dataframe_and_matching_references(env):
    app_context, dataset, other, chart = env
    command = RenameColumnCommand(app_context, dataset.id, 0, "time")

    assert command.execute() is True
    assert list(dataset.data.columns) == ["time", "b"]
    assert chart.data_series[0].x_column == "time"
    assert chart.data_series[0].y_column == "b"
    assert chart.fit_data[0].source_x_column == "time"
    # same column name in another dataset: untouched
    assert chart.data_series[1].x_column == "a"
    assert list(other.data.columns) == ["a"]


def test_undo_and_redo_round_trip(env):
    app_context, dataset, _, chart = env
    command = RenameColumnCommand(app_context, dataset.id, 0, "time")
    command.execute()

    command.undo()
    assert list(dataset.data.columns) == ["a", "b"]
    assert chart.data_series[0].x_column == "a"
    assert chart.fit_data[0].source_x_column == "a"

    command.redo()
    assert list(dataset.data.columns) == ["time", "b"]
    assert chart.data_series[0].x_column == "time"


def test_duplicate_name_rejected(env):
    app_context, dataset, _, _ = env
    command = RenameColumnCommand(app_context, dataset.id, 0, "b")
    assert command.execute() is False
    assert list(dataset.data.columns) == ["a", "b"]
    app_context.get_ui_controller.return_value.show_error_message.assert_called_once()


def test_empty_name_rejected(env):
    app_context, dataset, _, _ = env
    command = RenameColumnCommand(app_context, dataset.id, 0, "   ")
    assert command.execute() is False
    assert list(dataset.data.columns) == ["a", "b"]


def test_unchanged_name_is_silent_noop(env):
    app_context, dataset, _, _ = env
    command = RenameColumnCommand(app_context, dataset.id, 0, "a")
    assert command.execute() is False
    assert list(dataset.data.columns) == ["a", "b"]
    app_context.get_ui_controller.return_value.show_error_message.assert_not_called()


def test_events_emitted_only_for_affected_charts(env):
    app_context, dataset, _, chart = env
    command = RenameColumnCommand(app_context, dataset.id, 0, "time")
    command.execute()

    renamed_calls = [c for c in app_context.event_bus.emit.call_args_list
                     if c.args[0] == DatasetOperationEvents.DATASET_COLUMN_RENAMED]
    assert len(renamed_calls) == 1
    assert renamed_calls[0].args[1]["old_name"] == "a"
    assert renamed_calls[0].args[1]["new_name"] == "time"

    updated = _chart_updated_calls(app_context)
    assert len(updated) == 1  # 'untouched_chart' gets no event
    assert updated[0].args[1]["chart_id"] == chart.id
    assert "chart" in updated[0].args[1]
