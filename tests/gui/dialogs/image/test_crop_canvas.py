import pytest
from PySide6.QtCore import QPoint, QRect
from PySide6.QtGui import QImage
from PySide6.QtWidgets import QApplication

from pandaplot.gui.dialogs.image.crop_canvas import CropCanvas

from PySide6.QtCore import QEvent, QPointF
from PySide6.QtGui import QMouseEvent


def _mouse_event(event_type: QEvent.Type, pos: QPoint) -> QMouseEvent:
    # Uses the (local, global) overload rather than the 5-positional-arg one
    # (type, localPos, button, buttons, modifiers) -- the latter is flagged
    # deprecated by PySide6 even when a device is supplied explicitly.
    from PySide6.QtCore import Qt as _Qt
    point = QPointF(pos)
    return QMouseEvent(event_type, point, point, _Qt.MouseButton.LeftButton,
                        _Qt.MouseButton.LeftButton, _Qt.KeyboardModifier.NoModifier)


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


class TestCropCanvasResizeFromHandle:
    def test_br_handle_no_aspect_lock_resizes_freely(self):
        canvas = _make_canvas(image_size=(100, 100))
        rect = QRect(0, 0, 50, 50)
        result = canvas.resize_rect_from_handle(rect, "br", QPoint(80, 40))
        assert result == QRect(0, 0, 80, 40)

    def test_tl_handle_moves_top_left_corner(self):
        canvas = _make_canvas(image_size=(100, 100))
        rect = QRect(10, 10, 50, 50)  # (10,10)-(60,60)
        result = canvas.resize_rect_from_handle(rect, "tl", QPoint(20, 30))
        assert result == QRect(20, 30, 40, 30)  # right/bottom (60,60) stay fixed

    def test_resize_clamps_to_image_bounds(self):
        canvas = _make_canvas(image_size=(100, 100))
        rect = QRect(0, 0, 50, 50)
        result = canvas.resize_rect_from_handle(rect, "br", QPoint(500, 500))
        assert result == QRect(0, 0, 100, 100)

    def test_br_handle_with_aspect_lock_derives_height_from_width(self):
        canvas = _make_canvas(image_size=(200, 200))
        canvas.set_aspect_lock(2.0)  # width:height == 2:1
        rect = QRect(0, 0, 50, 50)
        result = canvas.resize_rect_from_handle(rect, "br", QPoint(80, 999))
        assert result.width() == 80
        assert result.height() == 40  # 80 / 2.0
        assert result.topLeft() == QPoint(0, 0)  # tl anchor unaffected by drag y

    def test_tm_handle_with_aspect_lock_derives_width_anchored_at_left(self):
        canvas = _make_canvas(image_size=(200, 200))
        canvas.set_aspect_lock(2.0)
        rect = QRect(10, 10, 60, 60)  # (10,10)-(70,70)
        result = canvas.resize_rect_from_handle(rect, "tm", QPoint(999, 40))
        assert result.top() == 40
        assert result.height() == 30  # bottom (70) - top (40)
        assert result.width() == 60  # 30 * 2.0
        assert result.left() == 10  # anchored

    def test_ml_handle_with_aspect_lock_derives_height_anchored_at_top(self):
        canvas = _make_canvas(image_size=(200, 200))
        canvas.set_aspect_lock(2.0)
        rect = QRect(10, 10, 60, 60)  # (10,10)-(70,70)
        result = canvas.resize_rect_from_handle(rect, "ml", QPoint(40, 999))
        assert result.left() == 40
        assert result.width() == 30  # right (70) - left (40)
        assert result.height() == 15  # 30 / 2.0
        assert result.top() == 10  # anchored


class TestCropCanvasMove:
    def test_move_rect_translates(self):
        canvas = _make_canvas(image_size=(100, 100))
        rect = QRect(10, 10, 20, 20)
        result = canvas.move_rect(rect, QPoint(5, -5))
        assert result == QRect(15, 5, 20, 20)

    def test_move_rect_clamps_to_bounds(self):
        canvas = _make_canvas(image_size=(100, 100))
        rect = QRect(90, 90, 20, 20)  # already partly out of bounds on the right/bottom
        result = canvas.move_rect(rect, QPoint(50, 50))
        assert result.right() <= 99
        assert result.bottom() <= 99
        assert result.width() == 20
        assert result.height() == 20


class TestCropCanvasAspectLock:
    def test_set_aspect_lock_reflows_current_rect_and_emits_signal(self, qtbot=None):
        canvas = _make_canvas(image_size=(200, 200))
        canvas.set_crop_rect(QRect(0, 0, 100, 100))
        received = []
        canvas.cropRectChanged.connect(received.append)

        canvas.set_aspect_lock(2.0)

        assert len(received) == 1
        assert received[0].width() == 100
        assert received[0].height() == 50


class TestCropCanvasMouseDrag:
    def test_dragging_body_moves_rect_and_emits_signal(self):
        canvas = _make_canvas(widget_size=(200, 200), image_size=(100, 100))
        canvas.set_crop_rect(QRect(20, 20, 40, 40))  # widget-space (40,40)-(120,120)
        received = []
        canvas.cropRectChanged.connect(received.append)

        canvas.mousePressEvent(_mouse_event(QEvent.Type.MouseButtonPress, QPoint(60, 60)))
        canvas.mouseMoveEvent(_mouse_event(QEvent.Type.MouseMove, QPoint(70, 60)))
        canvas.mouseReleaseEvent(_mouse_event(QEvent.Type.MouseButtonRelease, QPoint(70, 60)))

        assert len(received) == 1
        # 10 widget px at 2x scale (200 widget / 100 image) == 5 image px
        assert canvas.crop_rect().left() == 25

    def test_dragging_outside_rect_does_nothing(self):
        canvas = _make_canvas(widget_size=(200, 200), image_size=(100, 100))
        canvas.set_crop_rect(QRect(20, 20, 40, 40))
        original = canvas.crop_rect()

        canvas.mousePressEvent(_mouse_event(QEvent.Type.MouseButtonPress, QPoint(5, 5)))
        canvas.mouseMoveEvent(_mouse_event(QEvent.Type.MouseMove, QPoint(50, 50)))

        assert canvas.crop_rect() == original

    def test_paint_event_does_not_raise_on_null_image(self):
        canvas = CropCanvas()
        canvas.resize(100, 100)
        canvas.repaint()  # must not raise even with no image loaded
