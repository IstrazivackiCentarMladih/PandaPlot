"""Simple modal dialog showing a single image at full (capped) size."""

from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QDialog, QLabel, QVBoxLayout, QWidget

_MAX_WIDTH = 1200
_MAX_HEIGHT = 900


class ImageLightboxDialog(QDialog):
    """Modal full-size image preview, closed via Esc or a click on the image."""

    def __init__(self, pixmap: QPixmap, title: str, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setWindowTitle(title)

        scaled = pixmap
        if pixmap.width() > _MAX_WIDTH or pixmap.height() > _MAX_HEIGHT:
            scaled = pixmap.scaled(
                _MAX_WIDTH, _MAX_HEIGHT,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )

        label = QLabel()
        label.setPixmap(scaled)
        label.mousePressEvent = lambda event: self.close()  # noqa: ARG005 - Qt event signature

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(label)
