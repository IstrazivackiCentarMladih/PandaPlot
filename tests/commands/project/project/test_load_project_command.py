"""Tests for LoadProjectCommand (#209): no success dialog on load, and
opting out of CommandExecutor's generic dirty-tracking hook."""
from unittest.mock import Mock

from pandaplot.commands.project.project.load_project_command import LoadProjectCommand


def _make_app_context():
    return Mock()


def test_marks_project_modified_is_false():
    """A freshly loaded project starts with nothing unsaved -- AppState.
    load_project (called from _on_load_result) sets that directly, so this
    must not be double-counted by CommandExecutor's generic
    on_project_modified hook."""
    assert LoadProjectCommand.marks_project_modified is False


def test_on_load_result_does_not_show_a_success_dialog():
    """Regression (#209): loading a project used to pop an "loaded
    successfully" info dialog on every load -- unnecessary interruption for
    a routine, already-visible-in-the-UI action."""
    app_context = _make_app_context()
    command = LoadProjectCommand(app_context, "/p.pplot")

    project = Mock()
    project.name = "P"
    command._on_load_result({"success": True, "project": project, "file_path": "/p.pplot"})

    app_context.get_ui_controller.return_value.show_info_message.assert_not_called()


def test_on_load_result_still_loads_the_project_into_app_state():
    app_context = _make_app_context()
    command = LoadProjectCommand(app_context, "/p.pplot")

    project = Mock()
    project.name = "P"
    command._on_load_result({"success": True, "project": project, "file_path": "/p.pplot"})

    command.app_state.load_project.assert_called_once_with(project)


def test_on_load_result_invokes_the_on_loaded_callback():
    app_context = _make_app_context()
    calls = []
    command = LoadProjectCommand(app_context, "/p.pplot", on_loaded=lambda p: calls.append(p))

    project = Mock()
    project.name = "P"
    command._on_load_result({"success": True, "project": project, "file_path": "/p.pplot"})

    assert calls == [project]
