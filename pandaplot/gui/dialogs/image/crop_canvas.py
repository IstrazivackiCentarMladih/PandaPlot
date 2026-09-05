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
from PySide6.QtGui import QImage
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
