"""Tests for the wizard Type step's Colormap/Heatmap preview."""
import sys

import pytest
from matplotlib.collections import PathCollection, QuadMesh
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from pandaplot.app import build_app_context
from pandaplot.gui.dialogs.chart.chart_type_page import ChartTypePage


@pytest.fixture(scope="module", autouse=True)
def qapp():
    yield QApplication.instance() or QApplication(sys.argv)


def _select_row(page: ChartTypePage, chart_type: str) -> None:
    row = next(
        row for row in range(page.type_list.count())
        if page.type_list.item(row).data(Qt.ItemDataRole.UserRole) == chart_type
    )
    page.type_list.setCurrentRow(row)


def test_selecting_colormap_renders_a_scatter_preview():
    app_context = build_app_context()
    page = ChartTypePage(app_context=app_context)

    _select_row(page, "colormap")

    scatters = [c for c in page._preview_canvas.axes.collections if isinstance(c, PathCollection)]
    assert len(scatters) == 1


def test_selecting_heatmap_renders_a_pcolormesh_preview():
    app_context = build_app_context()
    page = ChartTypePage(app_context=app_context)

    _select_row(page, "heatmap")

    meshes = [c for c in page._preview_canvas.axes.collections if isinstance(c, QuadMesh)]
    assert len(meshes) == 1
