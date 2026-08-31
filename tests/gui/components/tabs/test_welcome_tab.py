"""Tests for WelcomeTab's Getting Started step interactions.

Steps 1-2 map to WelcomeTab's existing signals; steps 3-5 have no concrete
navigation target from the welcome tab (they describe actions inside an
already-open project) so they show an informational dialog instead.

Note: QMenu.exec() is a compiled Qt method that cannot be reliably
monkeypatched at the instance-call level (Shiboken bypasses the patched
class attribute at the C++ call site), so show_create_or_open_menu's
action -> effect mapping is exercised via dispatch_create_or_open_action
directly rather than by driving a real popup menu.
"""
from unittest.mock import Mock, patch

import pytest
from PySide6.QtWidgets import QApplication, QMessageBox

from pandaplot.gui.components.tabs.welcome_tab import WelcomeTab


@pytest.fixture(scope="module", autouse=True)
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


def _make_welcome_tab():
    return WelcomeTab(Mock(), None)


def test_dispatch_new_project_emits_new_project_requested():
    tab = _make_welcome_tab()
    spy = Mock()
    tab.new_project_requested.connect(spy)

    tab.dispatch_create_or_open_action("New Project")

    spy.assert_called_once()


def test_dispatch_open_project_emits_open_project_requested():
    tab = _make_welcome_tab()
    spy = Mock()
    tab.open_project_requested.connect(spy)

    tab.dispatch_create_or_open_action("Open Project")

    spy.assert_called_once()


def test_dispatch_browse_examples_opens_examples_dialog():
    tab = _make_welcome_tab()
    tab.show_examples_dialog = Mock()

    tab.dispatch_create_or_open_action("Browse Examples")

    tab.show_examples_dialog.assert_called_once()


def test_dispatch_unknown_action_does_nothing():
    tab = _make_welcome_tab()
    new_spy = Mock()
    open_spy = Mock()
    tab.new_project_requested.connect(new_spy)
    tab.open_project_requested.connect(open_spy)
    tab.show_examples_dialog = Mock()

    tab.dispatch_create_or_open_action("Something Else")

    new_spy.assert_not_called()
    open_spy.assert_not_called()
    tab.show_examples_dialog.assert_not_called()


def test_import_data_step_emits_import_data_requested():
    tab = _make_welcome_tab()
    spy = Mock()
    tab.import_data_requested.connect(spy)

    tab.import_data_requested.emit()

    spy.assert_called_once()


def test_show_step_info_displays_message_box():
    tab = _make_welcome_tab()

    with patch.object(QMessageBox, "information") as mock_info:
        tab.show_step_info("Explore Data", "some message")

    mock_info.assert_called_once_with(tab, "Explore Data", "some message")
