"""Tests for SaveProjectCommand / SaveProjectAsCommand logging behavior."""

import logging
from unittest.mock import Mock

from pandaplot.commands.project.project.save_project_command import (
    SaveProjectAsCommand,
    SaveProjectCommand,
)


def _make_app_context(has_project=True, current_project=None, project_file_path=None):
    app_state = Mock()
    app_state.has_project = has_project
    app_state.current_project = current_project
    app_state.project_file_path = project_file_path

    app_context = Mock()
    app_context.get_app_state.return_value = app_state
    app_context.get_ui_controller.return_value = Mock()
    return app_context, app_state


def test_execute_logs_a_warning_when_save_already_in_progress(caplog):
    app_context, app_state = _make_app_context()
    command = SaveProjectCommand(app_context)
    command.is_saving = True

    with caplog.at_level(logging.WARNING):
        assert command.execute() is False
    assert "SaveProjectCommand.execute" in caplog.text


def test_execute_logs_a_warning_when_no_project_loaded(caplog):
    app_context, app_state = _make_app_context(has_project=False)
    command = SaveProjectCommand(app_context)

    with caplog.at_level(logging.WARNING):
        assert command.execute() is False
    assert "SaveProjectCommand.execute" in caplog.text


def test_execute_logs_a_warning_when_current_project_none(caplog):
    app_context, app_state = _make_app_context(has_project=True, current_project=None)
    command = SaveProjectCommand(app_context)

    with caplog.at_level(logging.WARNING):
        assert command.execute() is False
    assert "SaveProjectCommand.execute" in caplog.text


def test_save_as_execute_logs_a_warning_when_no_project_loaded(caplog):
    app_context, app_state = _make_app_context(has_project=False)
    command = SaveProjectAsCommand(app_context)

    with caplog.at_level(logging.WARNING):
        assert command.execute() is False
    assert "SaveProjectAsCommand.execute" in caplog.text


def test_save_as_execute_logs_a_warning_when_current_project_none(caplog):
    app_context, app_state = _make_app_context(has_project=True, current_project=None)
    command = SaveProjectAsCommand(app_context)

    with caplog.at_level(logging.WARNING):
        assert command.execute() is False
    assert "SaveProjectAsCommand.execute" in caplog.text


def test_marks_project_modified_is_false():
    """SaveProjectCommand clears AppState's dirty flag itself (via
    mark_saved) and must not be double-counted by CommandExecutor's generic
    on_project_modified hook. SaveProjectAsCommand inherits this."""
    assert SaveProjectCommand.marks_project_modified is False
    assert SaveProjectAsCommand.marks_project_modified is False


def test_on_save_result_marks_the_project_saved():
    """Regression (#209): a successful save must clear AppState.is_modified
    so the title bar / close confirmation stop treating the project as
    having unsaved changes."""
    project = Mock()
    project.name = "P"
    app_context, app_state = _make_app_context(has_project=True, current_project=project, project_file_path="/p.pplot")

    command = SaveProjectCommand(app_context)
    command.previous_file_path = "/p.pplot"
    command._on_save_result({"success": True, "project": project, "path": "/p.pplot"})

    app_state.mark_saved.assert_called_once()


def test_on_save_result_does_not_mark_saved_on_failure():
    app_context, app_state = _make_app_context()
    command = SaveProjectCommand(app_context)

    command._on_save_result({"success": False, "error": "disk full"})

    app_state.mark_saved.assert_not_called()
