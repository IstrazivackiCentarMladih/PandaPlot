"""Tests for the main menu's Chart menu."""
from unittest.mock import Mock

import pytest
from PySide6.QtWidgets import QApplication, QWidget

from pandaplot.gui.components.main_menu.main_menu import MainMenu
from pandaplot.models.project.items import Dataset


@pytest.fixture(scope="module", autouse=True)
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


def _fake_app_context(datasets):
    project = Mock()
    project.get_all_items.return_value = datasets

    app_state = Mock()
    app_state.has_project = True
    app_state.current_project = project

    app_context = Mock()
    app_context.get_app_state.return_value = app_state
    app_context.event_bus = Mock()
    app_context.get_manager.return_value = Mock()
    return app_context


def test_chart_menu_sits_between_data_and_settings():
    parent = QWidget()
    menu = MainMenu(parent=parent, app_context=_fake_app_context(datasets=[]))
    titles = [action.text() for action in menu.actions() if action.menu() is not None]
    menu_titles = [action.menu().title() for action in menu.actions() if action.menu() is not None]

    assert menu_titles.index("Chart") == menu_titles.index("Data") + 1
    assert menu_titles.index("Settings") == menu_titles.index("Chart") + 1


def test_create_new_action_disabled_with_no_datasets():
    parent = QWidget()
    menu = MainMenu(parent=parent, app_context=_fake_app_context(datasets=[]))

    assert menu.create_chart_action.isEnabled() is False


def test_create_new_action_enabled_with_a_dataset():
    dataset = Mock(spec=Dataset)
    parent = QWidget()
    menu = MainMenu(parent=parent, app_context=_fake_app_context(datasets=[dataset]))

    assert menu.create_chart_action.isEnabled() is True
