"""Tests for NewProjectCommand (#209): dedicated naming dialog and
dirty-aware replace confirmation. Also covers cleanup() (see Command.cleanup)."""
from unittest.mock import Mock

import pytest

from pandaplot.commands.base_command import CommandResult
from pandaplot.commands.project.project.new_project_command import NewProjectCommand
from pandaplot.models.events import EventBus
from pandaplot.models.state.app_state import AppState


def _make_app_context(*, has_project=False, is_modified=False):
    app_context = Mock()
    app_context.get_app_state.return_value.has_project = has_project
    app_context.get_app_state.return_value.is_modified = is_modified
    return app_context


def test_no_current_project_creates_without_confirmation():
    app_context = _make_app_context(has_project=False)
    app_context.get_ui_controller.return_value.show_new_project_dialog.return_value = "My Project"

    command = NewProjectCommand(app_context)
    assert command.execute() is CommandResult.SUCCESS

    app_context.get_ui_controller.return_value.show_question.assert_not_called()
    loaded = app_context.get_app_state.return_value.load_project.call_args.args[0]
    assert loaded.name == "My Project"


def test_unmodified_current_project_creates_without_confirmation():
    """Regression (#209): the old blanket confirmation fired even when the
    current project had nothing unsaved to lose."""
    app_context = _make_app_context(has_project=True, is_modified=False)
    app_context.get_ui_controller.return_value.show_new_project_dialog.return_value = "My Project"

    command = NewProjectCommand(app_context)
    assert command.execute() is CommandResult.SUCCESS

    app_context.get_ui_controller.return_value.show_question.assert_not_called()


def test_modified_current_project_asks_for_confirmation():
    app_context = _make_app_context(has_project=True, is_modified=True)
    app_context.get_ui_controller.return_value.show_question.return_value = True
    app_context.get_ui_controller.return_value.show_new_project_dialog.return_value = "My Project"

    command = NewProjectCommand(app_context)
    assert command.execute() is CommandResult.SUCCESS

    app_context.get_ui_controller.return_value.show_question.assert_called_once()
    app_context.get_app_state.return_value.load_project.assert_called_once()


def test_declining_confirmation_aborts_without_creating():
    app_context = _make_app_context(has_project=True, is_modified=True)
    app_context.get_ui_controller.return_value.show_question.return_value = False

    command = NewProjectCommand(app_context)
    assert command.execute() is CommandResult.FAILURE

    app_context.get_app_state.return_value.load_project.assert_not_called()


def test_cancelling_the_naming_dialog_aborts_without_creating():
    app_context = _make_app_context(has_project=False)
    app_context.get_ui_controller.return_value.show_new_project_dialog.return_value = None

    command = NewProjectCommand(app_context)
    assert command.execute() is CommandResult.NOOP

    app_context.get_app_state.return_value.load_project.assert_not_called()


def test_new_project_uses_the_entered_name():
    app_context = _make_app_context(has_project=False)
    app_context.get_ui_controller.return_value.show_new_project_dialog.return_value = "Custom Name"

    command = NewProjectCommand(app_context)
    command.execute()

    loaded = app_context.get_app_state.return_value.load_project.call_args.args[0]
    assert loaded.name == "Custom Name"


def test_marks_project_modified_is_false():
    """NewProjectCommand sets AppState's dirty flag itself (via
    load_project) and must not be double-counted by CommandExecutor's
    generic on_project_modified hook."""
    assert NewProjectCommand.marks_project_modified is False


def test_undo_restores_the_previous_projects_dirty_state():
    """Regression (PR #235 review): load_project() (called by undo() to
    restore the previous project) unconditionally clears is_modified, since
    it assumes a fresh disk load. Undoing NewProjectCommand instead restores
    a project that may still have had unsaved changes -- those must survive,
    not be silently reported as saved."""
    app_state = AppState(EventBus())
    previous_project = Mock()
    previous_project.name = "Previous"
    app_state.load_project(previous_project)
    app_state.mark_modified()

    app_context = Mock()
    app_context.get_app_state.return_value = app_state
    app_context.get_ui_controller.return_value.show_new_project_dialog.return_value = "New"

    command = NewProjectCommand(app_context)
    assert command.execute() is CommandResult.SUCCESS

    assert command.undo() is CommandResult.SUCCESS
    assert app_state.current_project is previous_project
    assert app_state.is_modified is True


@pytest.fixture
def env():
    app_state = Mock()
    app_state.has_project = True
    app_context = Mock()
    app_context.get_app_state.return_value = app_state
    app_context.get_ui_controller.return_value = Mock()
    return app_context


def test_cleanup_releases_the_previous_project_reference(env):
    command = NewProjectCommand(env)
    command.previous_project = Mock()

    command.cleanup()

    assert command.previous_project is None
