import pytest
from PySide6.QtCore import QPoint, QRect
from PySide6.QtGui import QImage
from PySide6.QtWidgets import QApplication

from pandaplot.gui.dialogs.image.crop_canvas import CropCanvas


@pytest.fixture(scope="module", autouse=True)
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


def _make_canvas(widget_size=(200, 200), image_size=(100, 100)) -> CropCanvas:
    canvas = CropCanvas()
    canvas.resize(*widget_size)
    canvas.set_image(QImage(*image_size, QImage.Format.Format_RGB32))
    return canvas


class TestCropCanvasInit:
    def test_set_image_initializes_crop_rect_to_full_bounds(self):
        canvas = _make_canvas(image_size=(80, 60))
        assert canvas.crop_rect() == QRect(0, 0, 80, 60)

    def test_set_crop_rect_clamps_out_of_bounds_rect(self):
        canvas = _make_canvas(image_size=(80, 60))
        canvas.set_crop_rect(QRect(-10, -10, 1000, 1000))
        assert canvas.crop_rect() == QRect(0, 0, 80, 60)


class TestCropCanvasHitTest:
    def test_hit_test_detects_top_left_handle(self):
        # 200x200 widget, 100x100 image -> displayed at 2x scale, filling
        # the widget exactly (both square), so image (0,0) maps to widget (0,0).
        canvas = _make_canvas(widget_size=(200, 200), image_size=(100, 100))
        assert canvas.hit_test(QPoint(1, 1)) == "tl"

    def test_hit_test_detects_bottom_right_handle(self):
        canvas = _make_canvas(widget_size=(200, 200), image_size=(100, 100))
        assert canvas.hit_test(QPoint(199, 199)) == "br"

    def test_hit_test_detects_body_away_from_handles(self):
        canvas = _make_canvas(widget_size=(200, 200), image_size=(100, 100))
        assert canvas.hit_test(QPoint(100, 100)) == "body"

    def test_hit_test_returns_none_outside_rect(self):
        canvas = _make_canvas(widget_size=(200, 200), image_size=(100, 100))
        canvas.set_crop_rect(QRect(20, 20, 40, 40))  # widget-space (40,40)-(120,120)
        assert canvas.hit_test(QPoint(5, 5)) is None
