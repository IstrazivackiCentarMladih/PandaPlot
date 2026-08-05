"""Tests for chart_type_icon."""
import pytest
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from pandaplot.gui.dialogs.chart.chart_type_icons import chart_type_icon


@pytest.fixture(scope="module", autouse=True)
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


@pytest.mark.parametrize("chart_type", ["line", "scatter", "bar", "hist"])
def test_icon_renders_a_non_empty_pixmap(chart_type):
    icon = chart_type_icon(chart_type, "#4A56C6")

    assert isinstance(icon, QIcon)
    pixmap = icon.pixmap(14, 14)
    assert not pixmap.isNull()


def test_unknown_chart_type_raises():
    with pytest.raises(KeyError):
        chart_type_icon("pie", "#4A56C6")
