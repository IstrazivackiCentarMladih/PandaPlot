"""Tests for CreateFitReportCommand execute, undo, and redo."""

import logging
from unittest.mock import Mock

import numpy as np
import pytest

from pandaplot.commands.base_command import CommandResult
from pandaplot.commands.project.fit.create_fit_report_command import CreateFitReportCommand
from pandaplot.models.project.items.dataset import Dataset
from pandaplot.models.project.items.note import Note
from pandaplot.models.project.project import Project


@pytest.fixture
def app_context_with_project():
    project = Project(name="Project")
    source = Dataset(name="Source")
    project.add_item(source)

    app_state = Mock()
    app_state.has_project = True
    app_state.current_project = project
    app_state.event_bus = Mock()

    app_context = Mock()
    app_context.get_app_state.return_value = app_state

    return app_context, project, source


@pytest.fixture
def fit_results():
    return Mock(
        fit_type="Linear (y = ax + b)",
        equation="y = 2*x + 1",
        param_names=["a", "b"],
        params={"a": 2.0, "b": 1.0},
        errors=np.array([0.1, 0.1]),
        r_squared=0.99,
        x_fit=np.array([1.0, 2.0, 3.0]),
        y_fit=np.array([3.0, 5.0, 7.0]),
        x_data=np.array([1.0, 2.0, 3.0]),
        confidence_lower=None,
        confidence_upper=None,
    )


def test_execute_creates_note_and_dataset(app_context_with_project, fit_results):
    app_context, project, source = app_context_with_project

    command = CreateFitReportCommand(
        app_context=app_context,
        fit_results=fit_results,
        source_dataset_id=source.id,
        source_x_column="x",
        source_y_column="y",
    )

    assert command.execute() is CommandResult.SUCCESS

    note = project.find_item(command.report_note_id)
    dataset = project.find_item(command.result_dataset_id)

    assert isinstance(note, Note)
    assert "Linear" in note.content
    assert "y = 2*x + 1" in note.content
    assert "R² = 0.990000" in note.content

    assert isinstance(dataset, Dataset)
    assert list(dataset.data["x"]) == [1.0, 2.0, 3.0]
    assert list(dataset.data["y"]) == [3.0, 5.0, 7.0]

    # Placed alongside the source dataset by default.
    assert note.parent_id == source.parent_id
    assert dataset.parent_id == source.parent_id


def test_execute_logs_a_warning_when_no_project_loaded(fit_results, caplog):
    app_state = Mock()
    app_state.has_project = False
    app_state.current_project = None
    app_context = Mock()
    app_context.get_app_state.return_value = app_state

    command = CreateFitReportCommand(
        app_context=app_context,
        fit_results=fit_results,
        source_dataset_id="ds1",
    )

    with caplog.at_level(logging.WARNING):
        assert command.execute() is CommandResult.FAILURE
    assert "no project" in caplog.text.lower()
    app_context.get_ui_controller.return_value.show_error_message.assert_called_once()


def test_undo_removes_note_and_dataset(app_context_with_project, fit_results):
    app_context, project, source = app_context_with_project

    command = CreateFitReportCommand(
        app_context=app_context,
        fit_results=fit_results,
        source_dataset_id=source.id,
    )

    command.execute()
    note_id = command.report_note_id
    dataset_id = command.result_dataset_id

    command.undo()

    assert project.find_item(note_id) is None
    assert project.find_item(dataset_id) is None


def test_redo_recreates_note_and_dataset(app_context_with_project, fit_results):
    app_context, project, source = app_context_with_project

    command = CreateFitReportCommand(
        app_context=app_context,
        fit_results=fit_results,
        source_dataset_id=source.id,
    )

    command.execute()
    command.undo()
    command.redo()

    assert project.find_item(command.report_note_id) is not None
    assert project.find_item(command.result_dataset_id) is not None


def test_cleanup_releases_the_result_ids(app_context_with_project, fit_results):
    app_context, project, source = app_context_with_project

    command = CreateFitReportCommand(
        app_context=app_context,
        fit_results=fit_results,
        source_dataset_id=source.id,
    )

    command.execute()
    assert command.report_note_id is not None
    assert command.result_dataset_id is not None

    command.cleanup()

    assert command.report_note_id is None
    assert command.result_dataset_id is None
