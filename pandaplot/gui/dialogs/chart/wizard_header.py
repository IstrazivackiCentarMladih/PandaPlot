"""Shared header row for the chart creation wizard: a small checkmark icon,
bold "Create chart" title, and a close (X) button, in a fixed 40px row.

Each `ChartWizard` page owns its own `WizardHeader` instance (same rationale
as `WizardStepRail`/`WizardFooter` -- `QWizard` swaps whole page widgets on
navigation, so there's no single persistent chrome region to share one
instance through). The header itself has no reference to the wizard; pages
connect `closeClicked` to `self.wizard().reject()` themselves, keeping this
widget independently testable (see test_wizard_header.py).
"""
from PySide6.QtCore import QPointF, QSize, Qt, Signal
from PySide6.QtGui import QIcon, QPainter, QPen, QPixmap
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QWidget

_HEADER_HEIGHT = 40
_CLOSE_BUTTON_SIZE = 22


def _checkmark_icon(color: str, size: int = 14) -> QIcon:
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    pen = QPen(color)
    pen.setWidthF(1.5)
    painter.setPen(pen)
    painter.drawPolyline([
        QPointF(size * 0.125, size * 0.84),
        QPointF(size * 0.375, size * 0.44),
        QPointF(size * 0.5625, size * 0.66),
        QPointF(size * 0.875, size * 0.19),
    ])
    painter.end()
    return QIcon(pixmap)


def _close_icon(color: str, size: int = 11) -> QIcon:
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    pen = QPen(color)
    pen.setWidthF(1.5)
    painter.setPen(pen)
    painter.drawLine(QPointF(size * 0.22, size * 0.22), QPointF(size * 0.78, size * 0.78))
    painter.drawLine(QPointF(size * 0.78, size * 0.22), QPointF(size * 0.22, size * 0.78))
    painter.end()
    return QIcon(pixmap)


class WizardHeader(QWidget):
    """40px header row: checkmark icon, bold "Create chart" title, close (X) button."""

    closeClicked = Signal()

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setFixedHeight(_HEADER_HEIGHT)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 0, 14, 0)
        layout.setSpacing(9)

        self.icon_label = QLabel(self)
        self.icon_label.setFixedSize(QSize(14, 14))
        layout.addWidget(self.icon_label)

        self.title_label = QLabel("Create chart", self)
        layout.addWidget(self.title_label, 1)

        self.close_button = QPushButton(self)
        self.close_button.setFlat(True)
        self.close_button.setFixedSize(QSize(_CLOSE_BUTTON_SIZE, _CLOSE_BUTTON_SIZE))
        self.close_button.setIconSize(QSize(11, 11))
        self.close_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.close_button.clicked.connect(self.closeClicked.emit)
        layout.addWidget(self.close_button)

        self.set_tokens({})

    def set_tokens(self, tokens: dict) -> None:
        # Cast to `str` before handing values to QPen/QColor: some callers'
        # tests exercise `_apply_theme` with a bare `Mock()` app_context
        # (`WizardFooter`/`WizardStepRail` only ever interpolate tokens into
        # QSS strings, so an unconfigured Mock value never reaches a real Qt
        # constructor there; this widget's icons paint with real QColor/QPen,
        # so it needs the same tolerance).
        accent = str(tokens.get("accent", "#4A56C6"))
        text_muted = str(tokens.get("text_muted", "#6B7280"))
        border = str(tokens.get("border_panel", "#E5E6EA"))

        self.icon_label.setPixmap(_checkmark_icon(accent).pixmap(14, 14))
        self.title_label.setStyleSheet("font-weight: 700; font-size: 12.5px;")
        self.close_button.setIcon(_close_icon(text_muted))
        self.close_button.setStyleSheet(
            f"QPushButton {{ border: none; border-radius: 5px; color: {text_muted}; }}"
        )
        self.setStyleSheet(f"border-bottom: 1px solid {border};")
