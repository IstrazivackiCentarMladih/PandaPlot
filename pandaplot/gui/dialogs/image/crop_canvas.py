"""
Interactive crop-selection canvas.

Displays a QImage scaled to fit the widget's current size, with an
always-present crop rectangle (in image-coordinate space, not widget/screen
space) that the user drags to move and resizes via 8 corner/edge handles.
There is no "draw a new rectangle from scratch" mode -- the rectangle always
exists, starting at the full image bounds.
"""
from typing import Dict, Optional

from PySide6.QtCore import QPoint, QRect, Qt, Signal
from PySide6.QtGui import QBrush, QColor, QImage, QMouseEvent, QPainter, QPaintEvent, QPen, QResizeEvent
from PySide6.QtWidgets import QWidget

_HANDLE_SIZE = 8
_HIT_MARGIN = 6
_HANDLE_NAMES = ("tl", "tm", "tr", "ml", "mr", "bl", "bm", "br")


def clamp_rect_to_bounds(rect: QRect, width: int, height: int) -> QRect:
    """Intersects rect with a 0,0,width,height box, normalizing first.
    Shared by CropCanvas and ImageEditorDialog so both clamp crop rects the
    same way against their own image-size source."""
    bounds = QRect(0, 0, width, height)
    clamped = rect.normalized().intersected(bounds)
    return clamped if not clamped.isEmpty() else QRect(0, 0, 1, 1)


class CropCanvas(QWidget):
    """Fit-to-widget image display with a draggable/resizable crop rectangle."""

    cropRectChanged = Signal(QRect)

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setMinimumSize(200, 200)
        self._image = QImage()
        self._crop_rect = QRect()
        self._aspect_lock: Optional[float] = None
        self._active_handle: Optional[str] = None
        self._drag_start_widget_pos: Optional[QPoint] = None
        self._drag_start_rect: QRect = QRect()

    # ---- public API -------------------------------------------------

    def set_image(self, image: QImage) -> None:
        self._image = image
        self._crop_rect = QRect(0, 0, image.width(), image.height())
        self.update()

    def crop_rect(self) -> QRect:
        return QRect(self._crop_rect)

    def set_crop_rect(self, rect: QRect) -> None:
        self._crop_rect = self._clamp_to_image(rect)
        self.update()

    def set_aspect_lock(self, ratio: Optional[float]) -> None:
        self._aspect_lock = ratio
        if ratio is not None and not self._crop_rect.isEmpty():
            reflowed = self._reflow_to_aspect(self._crop_rect, ratio)
            self._crop_rect = self._clamp_to_image(reflowed)
            self.update()
            self.cropRectChanged.emit(self.crop_rect())

    # ---- coordinate mapping ------------------------------------------

    def _display_rect(self) -> QRect:
        if self._image.isNull():
            return QRect()
        scaled = self._image.size().scaled(self.size(), Qt.AspectRatioMode.KeepAspectRatio)
        x = (self.width() - scaled.width()) // 2
        y = (self.height() - scaled.height()) // 2
        return QRect(x, y, scaled.width(), scaled.height())

    def _scale(self) -> float:
        display = self._display_rect()
        if display.isEmpty() or self._image.width() == 0:
            return 1.0
        return display.width() / self._image.width()

    def _image_to_widget(self, point: QPoint) -> QPoint:
        display = self._display_rect()
        scale = self._scale()
        return QPoint(display.x() + round(point.x() * scale), display.y() + round(point.y() * scale))

    def _widget_to_image(self, point: QPoint) -> QPoint:
        display = self._display_rect()
        scale = self._scale()
        if scale == 0:
            return QPoint(0, 0)
        raw = QPoint(round((point.x() - display.x()) / scale), round((point.y() - display.y()) / scale))
        return self._clamp_point_to_image(raw)

    def _clamp_point_to_image(self, point: QPoint) -> QPoint:
        x = max(0, min(point.x(), self._image.width()))
        y = max(0, min(point.y(), self._image.height()))
        return QPoint(x, y)

    def _clamp_to_image(self, rect: QRect) -> QRect:
        return clamp_rect_to_bounds(rect, self._image.width(), self._image.height())

    # ---- hit testing & pure geometry (unit-tested directly) -----------

    def _handle_widget_rects(self) -> Dict[str, QRect]:
        top_left = self._image_to_widget(self._crop_rect.topLeft())
        bottom_right = self._image_to_widget(self._crop_rect.bottomRight())
        mid_x = (top_left.x() + bottom_right.x()) // 2
        mid_y = (top_left.y() + bottom_right.y()) // 2
        centers = {
            "tl": QPoint(top_left.x(), top_left.y()), "tm": QPoint(mid_x, top_left.y()),
            "tr": QPoint(bottom_right.x(), top_left.y()),
            "ml": QPoint(top_left.x(), mid_y), "mr": QPoint(bottom_right.x(), mid_y),
            "bl": QPoint(top_left.x(), bottom_right.y()), "bm": QPoint(mid_x, bottom_right.y()),
            "br": QPoint(bottom_right.x(), bottom_right.y()),
        }
        half = _HANDLE_SIZE // 2 + _HIT_MARGIN
        return {name: QRect(c.x() - half, c.y() - half, half * 2, half * 2) for name, c in centers.items()}

    def hit_test(self, widget_pos: QPoint) -> Optional[str]:
        """Returns a handle name, "body", or None. Exposed directly so tests
        don't need to synthesize QMouseEvents to check hit-testing alone."""
        for name in _HANDLE_NAMES:
            if self._handle_widget_rects()[name].contains(widget_pos):
                return name
        crop_widget_rect = QRect(
            self._image_to_widget(self._crop_rect.topLeft()),
            self._image_to_widget(self._crop_rect.bottomRight()),
        )
        if crop_widget_rect.contains(widget_pos):
            return "body"
        return None

    def resize_rect_from_handle(self, rect: QRect, handle: str, new_point: QPoint) -> QRect:
        """Pure function: returns rect with `handle` dragged to new_point
        (image coordinates), honoring the current aspect lock if any.

        Builds the new rect from continuous (exclusive) left/top/right/
        bottom bounds -- right = left + width, bottom = top + height --
        rather than via QRect.setRight()/setBottom(). Those Qt methods use
        the inclusive convention right() == left() + width() - 1, which
        would add a spurious +1 to width/height whenever the right or
        bottom edge is the one being dragged.
        """
        left, top = rect.left(), rect.top()
        right, bottom = rect.left() + rect.width(), rect.top() + rect.height()
        if "l" in handle:
            left = new_point.x()
        if "r" in handle:
            right = new_point.x()
        if "t" in handle:
            top = new_point.y()
        if "b" in handle:
            bottom = new_point.y()
        r = QRect(left, top, right - left, bottom - top).normalized()
        if self._aspect_lock:
            r = self._apply_aspect_lock(rect, r, handle, self._aspect_lock)
        return self._clamp_to_image(r)

    def _apply_aspect_lock(self, old_rect: QRect, new_rect: QRect, handle: str, ratio: float) -> QRect:
        width = max(1, new_rect.width())
        height = max(1, new_rect.height())

        if handle in ("tm", "bm"):
            # Only the top/bottom edge is dragged; derive width from the
            # resulting height, anchored at the old left edge.
            width = max(1, round(height * ratio))
            return QRect(old_rect.left(), new_rect.top(), width, height)

        if handle in ("ml", "mr"):
            # Only the left/right edge is dragged; derive height from the
            # resulting width, anchored at the old top edge.
            height = max(1, round(width / ratio))
            return QRect(new_rect.left(), old_rect.top(), width, height)

        # Corner handle: derive height from the dragged width, anchored at
        # the opposite corner so that corner stays fixed on screen.
        height = max(1, round(width / ratio))
        anchor_x = old_rect.right() if "l" in handle else old_rect.left()
        anchor_y = old_rect.bottom() if "t" in handle else old_rect.top()
        left = anchor_x - width if "l" in handle else anchor_x
        top = anchor_y - height if "t" in handle else anchor_y
        return QRect(left, top, width, height)

    def move_rect(self, rect: QRect, delta: QPoint) -> QRect:
        """Pure function: translates rect by delta (image coordinates),
        clamped so it stays fully within the image bounds."""
        moved = rect.translated(delta)
        bounds = QRect(0, 0, self._image.width(), self._image.height())
        if moved.left() < bounds.left():
            moved.moveLeft(bounds.left())
        if moved.top() < bounds.top():
            moved.moveTop(bounds.top())
        if moved.right() > bounds.right():
            moved.moveRight(bounds.right())
        if moved.bottom() > bounds.bottom():
            moved.moveBottom(bounds.bottom())
        return moved

    def _reflow_to_aspect(self, rect: QRect, ratio: float) -> QRect:
        """Used when the aspect lock changes: keeps the rect's top-left and
        width fixed, derives height from the new ratio."""
        width = max(1, rect.width())
        height = max(1, round(width / ratio))
        return QRect(rect.left(), rect.top(), width, height)

    # ---- Qt event handlers -------------------------------------------

    def mousePressEvent(self, event: QMouseEvent) -> None:
        pos = event.position().toPoint()
        self._active_handle = self.hit_test(pos)
        if self._active_handle is not None:
            self._drag_start_widget_pos = pos
            self._drag_start_rect = QRect(self._crop_rect)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self._active_handle is None or self._drag_start_widget_pos is None:
            return
        pos = event.position().toPoint()
        if self._active_handle == "body":
            start_img = self._widget_to_image(self._drag_start_widget_pos)
            current_img = self._widget_to_image(pos)
            delta = QPoint(current_img.x() - start_img.x(), current_img.y() - start_img.y())
            new_rect = self.move_rect(self._drag_start_rect, delta)
        else:
            new_point = self._widget_to_image(pos)
            new_rect = self.resize_rect_from_handle(self._drag_start_rect, self._active_handle, new_point)
        self._crop_rect = new_rect
        self.update()
        self.cropRectChanged.emit(self.crop_rect())

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        self._active_handle = None
        self._drag_start_widget_pos = None

    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)
        self.update()

    def paintEvent(self, event: QPaintEvent) -> None:
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor("#202020"))
        if self._image.isNull():
            return

        display = self._display_rect()
        painter.drawImage(display, self._image)

        crop_widget_rect = QRect(
            self._image_to_widget(self._crop_rect.topLeft()),
            self._image_to_widget(self._crop_rect.bottomRight()),
        )

        overlay = QColor(0, 0, 0, 140)
        painter.fillRect(QRect(display.left(), display.top(), display.width(), crop_widget_rect.top() - display.top()), overlay)
        painter.fillRect(QRect(display.left(), crop_widget_rect.bottom(), display.width(), display.bottom() - crop_widget_rect.bottom()), overlay)
        painter.fillRect(QRect(display.left(), crop_widget_rect.top(), crop_widget_rect.left() - display.left(), crop_widget_rect.height()), overlay)
        painter.fillRect(QRect(crop_widget_rect.right(), crop_widget_rect.top(), display.right() - crop_widget_rect.right(), crop_widget_rect.height()), overlay)

        painter.setPen(QPen(QColor("white"), 1))
        painter.drawRect(crop_widget_rect)

        painter.setBrush(QBrush(QColor("white")))
        for handle_rect in self._handle_widget_rects().values():
            half = _HANDLE_SIZE // 2
            center = handle_rect.center()
            painter.drawRect(QRect(center.x() - half, center.y() - half, _HANDLE_SIZE, _HANDLE_SIZE))
