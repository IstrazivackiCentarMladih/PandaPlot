"""Tests for ApplyFitCommand execute, undo, and redo."""

import logging
from unittest.mock import Mock

import numpy as np
import pytest

from pandaplot.commands.base_command import CommandResult
from pandaplot.commands.project.chart.apply_fit_command import ApplyFitCommand
from pandaplot.models.project.items.chart import Chart
from pandaplot.models.project.items.dataset import Dataset
from pandaplot.models.project.items.folder import Folder
from pandaplot.models.project.items.note import Note
from pandaplot.models.project.project import Project


@pytest.fixture
def app_context_with_chart():
    project = Project(name="Project")
    folder = Folder(name="Data")
    project.add_item(folder)
    source = Dataset(name="Source")
    project.add_item(source, parent_id=folder.id)
    chart = Chart(name="Chart")
    project.add_item(chart)

    app_state = Mock()
    app_state.has_project = True
    app_state.current_project = project

    app_context = Mock()
    app_context.get_app_state.return_value = app_state
    app_context.event_bus = Mock()

    return app_context, project, chart, source


@pytest.fixture
def fit_results():
    return Mock(
        fit_type="linear",
        equation="y = 2*x",
        x_fit=np.array([1.0, 2.0, 3.0]),
        y_fit=np.array([2.0, 4.0, 6.0]),
        x_data=np.array([1.0, 2.0, 3.0]),
        param_names=["slope", "intercept"],
        params={"slope": 2.0, "intercept": 0.0},
        errors=np.array([0.1, 0.1]),
        r_squared=0.99,
        confidence_lower=None,
        confidence_upper=None,
    )


def test_execute_adds_fit_to_chart(app_context_with_chart, fit_results):
    app_context, project, chart, source = app_context_with_chart

    command = ApplyFitCommand(
        app_context=app_context,
        chart_id=chart.id,
        fit_results=fit_results,
        source_dataset_id=source.id,
        source_x_column_id="x_id",
        source_y_column_id="y_id",
        source_x_column="x",
        source_y_column="y",
        label="Linear fit",
    )

    assert command.execute() is CommandResult.SUCCESS

    assert len(chart.fit_data) == 1
    assert command.added_index == 0

    fit = chart.fit_data[0]

    assert fit.fit_type == "linear"
    assert list(fit.x_data) == [1.0, 2.0, 3.0]
    assert list(fit.y_data) == [2.0, 4.0, 6.0]
    assert fit.source_dataset_id == source.id
    assert fit.source_x_column_id == "x_id"
    assert fit.source_y_column_id == "y_id"
    assert fit.source_x_column == "x"
    assert fit.source_y_column == "y"
    assert fit.label == "Linear fit"
    assert fit.fit_params == {"slope": 2.0, "intercept": 0.0}
    assert fit.fit_stats == {"r_squared": 0.99}


def test_execute_creates_report_note_and_dataset(app_context_with_chart, fit_results):
    app_context, project, chart, source = app_context_with_chart

    command = ApplyFitCommand(
        app_context=app_context,
        chart_id=chart.id,
        fit_results=fit_results,
        source_dataset_id=source.id,
        source_x_column_id="x_id",
        source_y_column_id="y_id",
        source_x_column="x",
        source_y_column="y",
    )

    assert command.execute() is CommandResult.SUCCESS

    note = project.find_item(command.report_note_id)
    dataset = project.find_item(command.result_dataset_id)

    assert isinstance(note, Note)
    assert isinstance(dataset, Dataset)

    # Placed alongside the source dataset, not at the project root.
    assert note.parent_id == source.parent_id
    assert dataset.parent_id == source.parent_id

    assert "$$y = 2*x$$" in note.content
    assert "$slope = 2 \\pm 0.1$" in note.content
    assert "$R^2 = 0.990000$" in note.content
    assert "Data / Source" in note.content
    assert "1 to 3" in note.content

    assert list(dataset.data["x"]) == [1.0, 2.0, 3.0]
    assert list(dataset.data["y"]) == [2.0, 4.0, 6.0]


def test_execute_logs_a_warning_when_chart_not_found(fit_results, caplog):
    project = Mock()
    project.find_item.return_value = None
    app_state = Mock()
    app_state.has_project = True
    app_state.current_project = project
    app_context = Mock()
    app_context.get_app_state.return_value = app_state
    app_context.event_bus = Mock()

    command = ApplyFitCommand(
        app_context=app_context,
        chart_id="missing",
        fit_results=fit_results,
        source_dataset_id="ds1",
        source_x_column_id="x_id",
        source_y_column_id="y_id",
    )

    with caplog.at_level(logging.WARNING):
        assert command.execute() is CommandResult.FAILURE
    assert "missing" in caplog.text
    app_context.get_ui_controller.return_value.show_error_message.assert_called_once()


def test_undo_logs_a_warning_when_nothing_to_undo(app_context_with_chart, fit_results, caplog):
    app_context, project, chart, source = app_context_with_chart

    command = ApplyFitCommand(
        app_context=app_context,
        chart_id=chart.id,
        fit_results=fit_results,
        source_dataset_id=source.id,
        source_x_column_id="x_id",
        source_y_column_id="y_id",
    )

    # Undo without a prior successful execute: added_index is still None.
    with caplog.at_level(logging.WARNING):
        command.undo()
    assert chart.id in caplog.text


def test_undo_removes_fit_and_report_from_chart(app_context_with_chart, fit_results):
    app_context, project, chart, source = app_context_with_chart

    command = ApplyFitCommand(
        app_context=app_context,
        chart_id=chart.id,
        fit_results=fit_results,
        source_dataset_id=source.id,
        source_x_column_id="x_id",
        source_y_column_id="y_id",
    )

    assert command.execute() is CommandResult.SUCCESS
    assert len(chart.fit_data) == 1
    note_id = command.report_note_id
    dataset_id = command.result_dataset_id

    command.undo()

    assert len(chart.fit_data) == 0
    assert project.find_item(note_id) is None
    assert project.find_item(dataset_id) is None


def test_redo_adds_fit_and_report_again(app_context_with_chart, fit_results):
    app_context, project, chart, source = app_context_with_chart

    command = ApplyFitCommand(
        app_context=app_context,
        chart_id=chart.id,
        fit_results=fit_results,
        source_dataset_id=source.id,
        source_x_column_id="x_id",
        source_y_column_id="y_id",
    )

    command.execute()
    command.undo()

    assert len(chart.fit_data) == 0

    command.redo()

    assert len(chart.fit_data) == 1

    fit = chart.fit_data[0]
    assert fit.fit_type == "linear"
    assert list(fit.x_data) == [1.0, 2.0, 3.0]
    assert list(fit.y_data) == [2.0, 4.0, 6.0]

    assert project.find_item(command.report_note_id) is not None
    assert project.find_item(command.result_dataset_id) is not None


def test_cleanup_releases_the_added_index_and_report_ids(app_context_with_chart, fit_results):
    app_context, project, chart, source = app_context_with_chart

    command = ApplyFitCommand(
        app_context=app_context,
        chart_id=chart.id,
        fit_results=fit_results,
        source_dataset_id=source.id,
        source_x_column_id="x_id",
        source_y_column_id="y_id",
    )

    command.execute()
    assert command.added_index is not None
    assert command.report_note_id is not None
    assert command.result_dataset_id is not None

    command.cleanup()
    assert command.added_index is None
    assert command.report_note_id is None
    assert command.result_dataset_id is None
