"""Tests for chart_type_icon."""
import pytest
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from pandaplot.gui.dialogs.chart.chart_type_icons import chart_type_icon, _vector_arrow_geometry


@pytest.fixture(scope="module", autouse=True)
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


@pytest.mark.parametrize("chart_type", ["line", "scatter", "bar", "hist", "vector"])
def test_icon_renders_a_non_empty_pixmap(chart_type):
    icon = chart_type_icon(chart_type, "#4A56C6")

    assert isinstance(icon, QIcon)
    pixmap = icon.pixmap(14, 14)
    assert not pixmap.isNull()

    image = pixmap.toImage()
    has_painted_pixel = any(
        image.pixelColor(x, y).alpha() > 0
        for x in range(image.width())
        for y in range(image.height())
    )
    assert has_painted_pixel, f"{chart_type} icon appears fully transparent -- nothing was painted"


def test_unknown_chart_type_raises():
    with pytest.raises(KeyError):
        chart_type_icon("pie", "#4A56C6")


def test_vector_arrow_geometry_stays_within_canvas_bounds():
    """Regression test: both arrowhead wings on both arrows must stay inside
    the [0, size] icon canvas at the default size, otherwise the icon renders
    a clipped/asymmetric arrowhead."""
    size = 14
    for start, end, wings in _vector_arrow_geometry(size):
        for point in (start, end, *wings):
            assert 0 <= point.x() <= size, f"x={point.x()} out of [0, {size}]"
            assert 0 <= point.y() <= size, f"y={point.y()} out of [0, {size}]"
