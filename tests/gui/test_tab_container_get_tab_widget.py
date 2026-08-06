"""Tests for TabContainer.get_tab_widget."""
import pytest
from PySide6.QtWidgets import QApplication, QWidget

from pandaplot.gui.components.tabs.tab_container import TabContainer


@pytest.fixture(scope="module", autouse=True)
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


def test_get_tab_widget_returns_none_when_not_open():
    container = TabContainer.__new__(TabContainer)
    container.tabs = {}

    assert container.get_tab_widget("missing-id") is None


def test_get_tab_widget_returns_the_open_widget():
    container = TabContainer.__new__(TabContainer)
    widget = QWidget()
    container.tabs = {"ds-1": widget}

    assert container.get_tab_widget("ds-1") is widget
