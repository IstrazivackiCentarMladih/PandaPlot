"""Tests for ChartTypePage."""
from unittest.mock import Mock

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from pandaplot.gui.dialogs.chart.chart_type_page import ChartTypePage


@pytest.fixture(scope="module", autouse=True)
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


def _fake_app_context():
    app_context = Mock()
    app_context.event_bus = Mock()
    return app_context


def test_line_is_selected_by_default():
    page = ChartTypePage(app_context=_fake_app_context())

    assert page.selected_chart_type() == "line"
    assert page.isComplete() is True


def test_selecting_histogram_updates_selected_chart_type():
    page = ChartTypePage(app_context=_fake_app_context())
    histogram_row = next(
        row for row in range(page.type_list.count())
        if page.type_list.item(row).data(Qt.ItemDataRole.UserRole) == "hist"
    )

    page.type_list.setCurrentRow(histogram_row)

    assert page.selected_chart_type() == "hist"


def test_empty_button_emits_empty_requested():
    page = ChartTypePage(app_context=_fake_app_context())
    received = []
    page.emptyRequested.connect(lambda: received.append(True))

    page.empty_button.click()

    assert received == [True]


def test_importing_chart_type_page_does_not_import_matplotlib():
    import subprocess
    import sys

    code = (
        "import sys; "
        "import pandaplot.gui.dialogs.chart.chart_type_page; "
        "assert 'matplotlib' not in sys.modules, 'matplotlib was imported eagerly'"
    )
    result = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
