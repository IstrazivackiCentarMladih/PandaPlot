"""Tests for RenameColumnCommand.

Columns are referenced by stable id, so a rename remaps the column's name on the
owning dataset without rewriting the stored column names on series/fits. The
resolved column (id -> current name) follows the rename automatically.
"""

from unittest.mock import Mock

import numpy as np
import pandas as pd
import pytest

from pandaplot.commands.project.dataset.rename_column_command import RenameColumnCommand
from pandaplot.models.events.event_types import ChartEvents, DatasetOperationEvents
from pandaplot.models.project import Project
from pandaplot.models.project.items import Chart, Dataset
from pandaplot.models.project.items.dataset import resolve_column_name


@pytest.fixture
def env():
    project = Project("P")
    dataset = Dataset(name="ds", data=pd.DataFrame({"a": [1, 2], "b": [3, 4]}))
    other = Dataset(name="other", data=pd.DataFrame({"a": [5]}))
    project.add_item(dataset)
    project.add_item(other)

    chart = Chart(name="c")
    chart.add_data_series(dataset.id, "a", "b", label="s1",
                          x_column_id=dataset.get_column_id("a"),
                          y_column_id=dataset.get_column_id("b"))
    chart.add_data_series(other.id, "a", "a", label="s2",  # other dataset: must not change
                          x_column_id=other.get_column_id("a"),
                          y_column_id=other.get_column_id("a"))
    chart.add_fit_data(dataset.id, "a", "b", "Linear",
                       np.array([1.0]), np.array([2.0]),
                       source_x_column_id=dataset.get_column_id("a"),
                       source_y_column_id=dataset.get_column_id("b"))
    project.add_item(chart)

    untouched_chart = Chart(name="c2")
    untouched_chart.add_data_series(other.id, "a", "a", label="s3",
                                    x_column_id=other.get_column_id("a"),
                                    y_column_id=other.get_column_id("a"))
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


def _resolved(dataset, series):
    return (resolve_column_name(dataset, series.x_column_id, series.x_column),
            resolve_column_name(dataset, series.y_column_id, series.y_column))


def test_rename_updates_dataframe_and_resolves_references(env):
    app_context, dataset, other, chart = env
    command = RenameColumnCommand(app_context, dataset.id, 0, "time")

    assert command.execute() is True
    assert list(dataset.data.columns) == ["time", "b"]
    # The stored name is not rewritten, but the id resolves to the new name.
    assert _resolved(dataset, chart.data_series[0]) == ("time", "b")
    assert resolve_column_name(dataset, chart.fit_data[0].source_x_column_id,
                               chart.fit_data[0].source_x_column) == "time"
    assert resolve_column_name(dataset, chart.fit_data[0].source_y_column_id,
                               chart.fit_data[0].source_y_column) == "b"
    # same column name in another dataset: untouched
    assert _resolved(other, chart.data_series[1]) == ("a", "a")
    assert list(other.data.columns) == ["a"]


def test_rename_without_preexisting_ids_still_follows(env):
    """Legacy references (name only, no id) are anchored during the rename."""
    app_context, dataset, _, chart = env
    # Simulate a legacy series that references columns by name only.
    series = chart.data_series[0]
    series.x_column_id = ""
    series.y_column_id = ""

    RenameColumnCommand(app_context, dataset.id, 0, "time").execute()

    assert series.x_column_id  # backfilled
    assert _resolved(dataset, series) == ("time", "b")


def test_undo_and_redo_round_trip(env):
    app_context, dataset, _, chart = env
    command = RenameColumnCommand(app_context, dataset.id, 0, "time")
    command.execute()

    command.undo()
    assert list(dataset.data.columns) == ["a", "b"]
    assert _resolved(dataset, chart.data_series[0]) == ("a", "b")
    assert resolve_column_name(dataset, chart.fit_data[0].source_x_column_id,
                               chart.fit_data[0].source_x_column) == "a"

    command.redo()
    assert list(dataset.data.columns) == ["time", "b"]
    assert _resolved(dataset, chart.data_series[0]) == ("time", "b")


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


def test_undo_after_rejected_execute_is_a_noop(env):
    app_context, dataset, _, chart = env
    command = RenameColumnCommand(app_context, dataset.id, 0, "b")  # duplicate -> rejected
    assert command.execute() is False

    command.undo()  # CommandExecutor pushes commands even on failure; undo must not corrupt
    assert list(dataset.data.columns) == ["a", "b"]
    assert _resolved(dataset, chart.data_series[0]) == ("a", "b")

    command.redo()
    assert list(dataset.data.columns) == ["a", "b"]


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
