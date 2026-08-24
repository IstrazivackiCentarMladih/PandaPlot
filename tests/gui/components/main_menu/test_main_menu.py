"""Tests for MainMenu."""
from unittest.mock import Mock, patch

import pytest
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QApplication

from pandaplot.gui.components.main_menu.main_menu import MainMenu
from pandaplot.models.state.app_context import AppContext
from pandaplot.services.theme.theme_manager import ThemeManager

_FAKE_PALETTE = {
    "card_bg": "#FFFFFF",
    "base_fg": "#000000",
    "card_border": "#DDDDDD",
    "accent": "#4A90E2",
    "card_pressed": "#DEE2E6",
}


@pytest.fixture(scope="module", autouse=True)
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


@pytest.fixture
def app_context():
    ctx = Mock(spec=AppContext)
    ctx.event_bus = Mock()
    app_state = Mock()
    app_state.has_project = False
    app_state.current_project = None
    ctx.get_app_state.return_value = app_state

    theme_manager = Mock()
    theme_manager.get_surface_palette.return_value = dict(_FAKE_PALETTE)

    def _get_manager(manager_type, *args, **kwargs):
        if manager_type is ThemeManager:
            return theme_manager
        return Mock()

    ctx.get_manager.side_effect = _get_manager
    return ctx


def _find_help_action(menu: MainMenu, text: str) -> QAction:
    help_menu = next(m for m in menu.findChildren(type(menu.actions()[0].menu())) if m.title() == "Help")
    return next(a for a in help_menu.actions() if a.text() == text)


class TestMainMenuHelpMenu:
    def test_help_menu_has_open_example_project_action(self, app_context):
        menu = MainMenu(parent=None, app_context=app_context)

        action = _find_help_action(menu, "Open Example Project...")

        assert action is not None

    def test_open_example_project_loads_selected_example(self, app_context):
        menu = MainMenu(parent=None, app_context=app_context)
        command_executor = Mock()
        app_context.get_command_executor.return_value = command_executor

        with patch("pandaplot.gui.dialogs.examples_dialog.ExamplesDialog") as dialog_cls:
            dialog = dialog_cls.return_value
            dialog.exec.return_value = True
            dialog.selected_path = "/examples/sample.pplot"

            menu.show_examples_dialog()

        command_executor.execute_command.assert_called_once()
        executed_command = command_executor.execute_command.call_args[0][0]
        assert executed_command.file_path == "/examples/sample.pplot"

    def test_open_example_project_does_nothing_when_dialog_cancelled(self, app_context):
        menu = MainMenu(parent=None, app_context=app_context)
        command_executor = Mock()
        app_context.get_command_executor.return_value = command_executor

        with patch("pandaplot.gui.dialogs.examples_dialog.ExamplesDialog") as dialog_cls:
            dialog = dialog_cls.return_value
            dialog.exec.return_value = False
            dialog.selected_path = None

            menu.show_examples_dialog()

        command_executor.execute_command.assert_not_called()
