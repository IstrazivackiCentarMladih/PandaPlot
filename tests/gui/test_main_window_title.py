"""Tests for PandaMainWindow._update_window_title (#209).

Exercises the method directly against a lightweight stand-in (rather than
constructing a full PandaMainWindow, which builds the entire app UI) since
_update_window_title only touches self.app_context and self.setWindowTitle.
"""
from unittest.mock import Mock

from pandaplot.gui.main_window import PandaMainWindow


class _FakeMainWindow:
    """Stand-in exposing just what _update_window_title reads/writes."""

    def __init__(self, app_context):
        self.app_context = app_context
        self.title = None

    def setWindowTitle(self, title):  # noqa: N802 - matches Qt's method name
        self.title = title


def _make_window(has_project, project_name="P", is_modified=False):
    app_context = Mock()
    app_context.get_app_state.return_value.has_project = has_project
    app_context.get_app_state.return_value.current_project.name = project_name
    app_context.get_app_state.return_value.is_modified = is_modified
    return _FakeMainWindow(app_context)


def test_no_project_shows_plain_app_name():
    window = _make_window(has_project=False)
    PandaMainWindow._update_window_title(window)
    assert window.title == "PandaPlot"


def test_unmodified_project_shows_name_without_marker():
    window = _make_window(has_project=True, project_name="My Project", is_modified=False)
    PandaMainWindow._update_window_title(window)
    assert window.title == "My Project - PandaPlot"


def test_modified_project_shows_unsaved_marker():
    window = _make_window(has_project=True, project_name="My Project", is_modified=True)
    PandaMainWindow._update_window_title(window)
    assert window.title == "My Project* - PandaPlot"
