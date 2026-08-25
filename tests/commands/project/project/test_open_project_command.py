"""Tests for OpenProjectCommand logging and lifecycle behavior."""

import logging
from unittest.mock import Mock, patch

from pandaplot.commands.project.project.open_project_command import OpenProjectCommand


def _make_app_context(has_project=False, project_file_path=None, is_modified=False):
    app_context = Mock()
    app_context.app_state.has_project = has_project
    app_context.app_state.project_file_path = project_file_path
    app_context.app_state.is_modified = is_modified
    return app_context


def test_invalid_project_file_logs_a_warning(caplog):
    app_context = Mock()
    app_context.ui_controller.show_open_project_dialog.return_value = "bad_path.pplot"

    command = OpenProjectCommand(app_context)
    with patch.object(command.project_manager, "validate_project_file", return_value=False):
        with caplog.at_level(logging.WARNING):
            command.execute()

    assert command.was_executed is False
    assert "bad_path.pplot" in caplog.text


def test_reopening_the_already_open_project_skips_reload():
    """Regression (#209): selecting the file that's already open must switch
    to it (a no-op, since it's already current) instead of reloading from
    disk, which would discard undo history / in-memory edits."""
    app_context = _make_app_context(has_project=True, project_file_path="/p/current.pplot")
    app_context.ui_controller.show_open_project_dialog.return_value = "/p/current.pplot"

    command = OpenProjectCommand(app_context)
    with patch.object(command.project_manager, "validate_project_file", return_value=True):
        command.execute()

    assert command.was_executed is False
    assert command.load_command is None
    app_context.ui_controller.show_question.assert_not_called()


def test_opening_a_different_file_does_not_skip_reload():
    app_context = _make_app_context(has_project=True, project_file_path="/p/current.pplot", is_modified=False)
    app_context.ui_controller.show_open_project_dialog.return_value = "/p/other.pplot"

    command = OpenProjectCommand(app_context)
    with patch.object(command.project_manager, "validate_project_file", return_value=True):
        with patch(
            "pandaplot.commands.project.project.open_project_command.LoadProjectCommand"
        ) as load_cls:
            command.execute()

    assert command.was_executed is True
    load_cls.assert_called_once_with(app_context, "/p/other.pplot")


def test_opening_another_project_does_not_ask_when_unmodified():
    """No unsaved changes to lose -- must not interrupt with a confirmation."""
    app_context = _make_app_context(has_project=True, project_file_path="/p/current.pplot", is_modified=False)
    app_context.ui_controller.show_open_project_dialog.return_value = "/p/other.pplot"

    command = OpenProjectCommand(app_context)
    with patch.object(command.project_manager, "validate_project_file", return_value=True):
        with patch("pandaplot.commands.project.project.open_project_command.LoadProjectCommand"):
            command.execute()

    app_context.ui_controller.show_question.assert_not_called()
    assert command.was_executed is True


def test_opening_another_project_asks_when_modified():
    app_context = _make_app_context(has_project=True, project_file_path="/p/current.pplot", is_modified=True)
    app_context.ui_controller.show_open_project_dialog.return_value = "/p/other.pplot"
    app_context.ui_controller.show_question.return_value = True

    command = OpenProjectCommand(app_context)
    with patch.object(command.project_manager, "validate_project_file", return_value=True):
        with patch("pandaplot.commands.project.project.open_project_command.LoadProjectCommand"):
            command.execute()

    app_context.ui_controller.show_question.assert_called_once()
    assert command.was_executed is True


def test_opening_another_project_aborts_when_user_declines():
    app_context = _make_app_context(has_project=True, project_file_path="/p/current.pplot", is_modified=True)
    app_context.ui_controller.show_open_project_dialog.return_value = "/p/other.pplot"
    app_context.ui_controller.show_question.return_value = False

    command = OpenProjectCommand(app_context)
    with patch.object(command.project_manager, "validate_project_file", return_value=True):
        with patch(
            "pandaplot.commands.project.project.open_project_command.LoadProjectCommand"
        ) as load_cls:
            command.execute()

    assert command.was_executed is False
    load_cls.assert_not_called()


def test_execute_does_not_show_a_success_dialog():
    """Regression (#209): opening a project used to show an "Opened
    successfully" info dialog after merely *initiating* the (asynchronous)
    load -- both an unnecessary interruption and, since the load hadn't
    finished yet, liable to reference the wrong project."""
    app_context = _make_app_context(has_project=False)
    app_context.ui_controller.show_open_project_dialog.return_value = "/p/new.pplot"

    command = OpenProjectCommand(app_context)
    with patch.object(command.project_manager, "validate_project_file", return_value=True):
        with patch("pandaplot.commands.project.project.open_project_command.LoadProjectCommand"):
            command.execute()

    app_context.ui_controller.show_info_message.assert_not_called()


def test_marks_project_modified_is_false():
    """OpenProjectCommand delegates all state changes to LoadProjectCommand/
    AppState and must not be double-counted by CommandExecutor's generic
    on_project_modified hook."""
    assert OpenProjectCommand.marks_project_modified is False
