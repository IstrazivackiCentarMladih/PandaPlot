"""Tests for SaveProjectCommand / SaveProjectAsCommand logging behavior."""

import logging
from unittest.mock import Mock

from pandaplot.commands.project.project.save_project_command import (
    SaveProjectAsCommand,
    SaveProjectCommand,
)
from pandaplot.models.events import EventBus
from pandaplot.models.state.app_state import AppState


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


def _make_real_app_context(project_file_path):
    """A real AppState (not a Mock) with a project already loaded and
    modified -- needed to exercise mark_saved's revision-guard logic, which
    a Mock's recorded-call-args can't meaningfully stand in for."""
    app_state = AppState(EventBus())
    project = Mock()
    project.name = "P"
    project.project_file_path = project_file_path
    app_state.load_project(project)
    app_state.mark_modified()

    app_context = Mock()
    app_context.get_app_state.return_value = app_state
    app_context.get_ui_controller.return_value = Mock()
    app_context.get_manager.return_value = Mock()
    return app_context, app_state, project


def test_on_save_result_skips_clearing_modified_when_a_newer_edit_happened_during_save():
    """Regression: a save that started at revision N must not clear
    is_modified if another command modified the project in the async gap
    between the background save finishing and this callback running --
    that edit isn't reflected in what was actually written to disk."""
    app_context, app_state, project = _make_real_app_context("/p.pplot")

    command = SaveProjectCommand(app_context)
    command.previous_file_path = "/p.pplot"
    command._save_started_revision = app_state.modification_revision  # as execute() would capture it

    app_state.mark_modified()  # a newer edit lands before _on_save_result runs

    command._on_save_result({"success": True, "project": project, "path": "/p.pplot"})

    assert app_state.is_modified is True


def test_on_save_result_clears_modified_when_no_newer_edit_happened():
    app_context, app_state, project = _make_real_app_context("/p.pplot")

    command = SaveProjectCommand(app_context)
    command.previous_file_path = "/p.pplot"
    command._save_started_revision = app_state.modification_revision

    command._on_save_result({"success": True, "project": project, "path": "/p.pplot"})

    assert app_state.is_modified is False


def test_on_save_result_restores_modified_after_path_change_when_a_newer_edit_happened():
    """save_path != previous_file_path takes the load_project() branch,
    which unconditionally clears is_modified as a side effect of installing
    the (same) project object under its new path -- a newer edit during
    that async gap must still survive that reset."""
    app_context, app_state, project = _make_real_app_context("/new.pplot")

    command = SaveProjectCommand(app_context)
    command.previous_file_path = "/old.pplot"  # different -> triggers the load_project branch
    command._save_started_revision = app_state.modification_revision

    app_state.mark_modified()  # a newer edit lands before _on_save_result runs

    command._on_save_result({"success": True, "project": project, "path": "/new.pplot"})

    assert app_state.is_modified is True
