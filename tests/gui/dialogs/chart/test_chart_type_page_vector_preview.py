"""Tests for the wizard Type step's Vector preview."""
import sys

import pytest
from matplotlib.quiver import Quiver
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from pandaplot.app import build_app_context
from pandaplot.gui.dialogs.chart.chart_type_page import ChartTypePage


@pytest.fixture(scope="module", autouse=True)
def qapp():
    yield QApplication.instance() or QApplication(sys.argv)


def test_selecting_vector_renders_a_quiver_preview():
    app_context = build_app_context()
    page = ChartTypePage(app_context=app_context)

    vector_row = next(
        row for row in range(page.type_list.count())
        if page.type_list.item(row).data(Qt.ItemDataRole.UserRole) == "vector"
    )
    page.type_list.setCurrentRow(vector_row)

    quivers = [c for c in page._preview_canvas.axes.collections if isinstance(c, Quiver)]
    assert len(quivers) == 1
