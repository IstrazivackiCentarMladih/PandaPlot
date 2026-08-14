"""Modal dialog showing one image at a time from an ordered list, with
Previous/Next navigation across the list without closing the dialog."""

from typing import Callable, List, Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QKeyEvent, QPixmap
from PySide6.QtWidgets import QDialog, QHBoxLayout, QLabel, QVBoxLayout, QWidget

from pandaplot.gui.components.common.image_thumbnail_tile import build_gallery_tile_icon
from pandaplot.gui.components.common.p_button import PButton
from pandaplot.models.project.items import Image

_MAX_WIDTH = 1200
_MAX_HEIGHT = 900


class ImageLightboxDialog(QDialog):
    """
    Modal full-size image preview over an ordered list of sibling Images,
    with Previous/Next buttons and Left/Right arrow keys to move between
    them without closing the dialog. Disabled (not wrapped) at either end.
    """

    def __init__(self, images: List[Image], start_index: int,
                 load_pixmap: Callable[[Image], Optional[QPixmap]],
                 parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._images = images
        self._index = start_index
        self._load_pixmap = load_pixmap

        self.image_label = QLabel()
        self.image_label.mousePressEvent = lambda event: self.close()  # noqa: ARG005 - Qt event signature

        self.previous_button = PButton("◀ Previous", on_click=self._go_previous)
        self.next_button = PButton("Next ▶", on_click=self._go_next)
        nav_row = QHBoxLayout()
        nav_row.addWidget(self.previous_button)
        nav_row.addStretch()
        nav_row.addWidget(self.next_button)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.image_label)
        layout.addLayout(nav_row)

        self._render_current()

    def _current_image(self) -> Image:
        return self._images[self._index]

    def _render_current(self) -> None:
        image = self._current_image()
        self.setWindowTitle(image.name)

        pixmap = self._load_pixmap(image)
        if pixmap is None:
            tokens = {}
            icon = build_gallery_tile_icon(None, "broken", False, tokens, size=_scaled_size(300, 300))
            self.image_label.setPixmap(icon.pixmap(icon.availableSizes()[0]))
        else:
            scaled = pixmap
            if pixmap.width() > _MAX_WIDTH or pixmap.height() > _MAX_HEIGHT:
                scaled = pixmap.scaled(
                    _MAX_WIDTH, _MAX_HEIGHT,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
            self.image_label.setPixmap(scaled)

        self.previous_button.setEnabled(self._index > 0)
        self.next_button.setEnabled(self._index < len(self._images) - 1)

    def _go_previous(self) -> None:
        if self._index <= 0:
            return
        self._index -= 1
        self._render_current()

    def _go_next(self) -> None:
        if self._index >= len(self._images) - 1:
            return
        self._index += 1
        self._render_current()

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() == Qt.Key.Key_Left:
            self._go_previous()
        elif event.key() == Qt.Key.Key_Right:
            self._go_next()
        else:
            super().keyPressEvent(event)


def _scaled_size(width: int, height: int):
    from PySide6.QtCore import QSize
    return QSize(width, height)
