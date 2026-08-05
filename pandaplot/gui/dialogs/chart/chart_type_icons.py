"""Small line-drawn icons for the chart-type list on the wizard's Type step.

Drawn with QPainter primitives (no SVG/asset files) so there's nothing to
ship or theme separately -- `color` is passed in by the caller (typically the
current design token's `accent` or `text_secondary`) each time the theme
changes.
"""
from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QIcon, QPainter, QPen, QPixmap


def _paint_line(painter: QPainter, size: int):
    points = [QPointF(1, size - 3), QPointF(size * 0.4, size * 0.45),
              QPointF(size * 0.65, size * 0.65), QPointF(size - 1, 2)]
    painter.drawPolyline(points)


def _paint_scatter(painter: QPainter, size: int):
    painter.setBrush(painter.pen().color())
    for x, y in ((size * 0.25, size * 0.7), (size * 0.5, size * 0.35), (size * 0.75, size * 0.55)):
        painter.drawEllipse(QRectF(x - 1.5, y - 1.5, 3, 3))


def _paint_bar(painter: QPainter, size: int):
    bars = [(1, size * 0.5, 3, size * 0.4), (size * 0.4, size * 0.25, 3, size * 0.65),
            (size * 0.7, size * 0.4, 3, size * 0.5)]
    for x, y, w, h in bars:
        painter.drawRect(QRectF(x, y, w, h))


def _paint_hist(painter: QPainter, size: int):
    bars = [(1, size * 0.65, 3, size * 0.25), (size * 0.35, size * 0.3, 3, size * 0.6),
            (size * 0.65, size * 0.5, 3, size * 0.4)]
    for x, y, w, h in bars:
        painter.drawRect(QRectF(x, y, w, h))


_PAINTERS = {
    "line": _paint_line,
    "scatter": _paint_scatter,
    "bar": _paint_bar,
    "hist": _paint_hist,
}


def chart_type_icon(chart_type: str, color: str, size: int = 14) -> QIcon:
    """Render `chart_type`'s icon at `size`x`size` in `color`.

    Raises:
        KeyError: if `chart_type` isn't one of "line"/"scatter"/"bar"/"hist".
    """
    paint_fn = _PAINTERS[chart_type]

    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    pen = QPen(color)
    pen.setWidthF(1.5)
    painter.setPen(pen)
    paint_fn(painter, size)
    painter.end()
    return QIcon(pixmap)
