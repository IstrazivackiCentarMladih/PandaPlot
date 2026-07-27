from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QIcon, QPainter, QPen, QPixmap

from pandaplot.models.chart.chart_configuration import LineStyleType

_PEN_STYLE_MAP = {
    LineStyleType.SOLID: Qt.PenStyle.SolidLine,
    LineStyleType.DASHED: Qt.PenStyle.DashLine,
    LineStyleType.DOTTED: Qt.PenStyle.DotLine,
    LineStyleType.DASHDOT: Qt.PenStyle.DashDotLine,
    LineStyleType.NONE: Qt.PenStyle.NoPen,
}


def line_style_pen_style(line_style: LineStyleType) -> Qt.PenStyle:
    """Map a LineStyleType to the matching Qt.PenStyle for drawing a sample."""
    return _PEN_STYLE_MAP[line_style]


def build_line_style_icon(
    line_style: LineStyleType, tokens: dict, size: QSize | None = None
) -> QIcon:
    """Draw a short horizontal line sample in the given style, for use as a
    combo-box item icon (design review: "line style -> dropdown with a drawn
    line sample per item")."""
    size = size or QSize(32, 16)
    pixmap = QPixmap(size)
    pixmap.fill(Qt.GlobalColor.transparent)

    pen_style = line_style_pen_style(line_style)
    if pen_style != Qt.PenStyle.NoPen:
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        pen = QPen(pen_style)
        pen.setColor(tokens.get("text_primary", "#1C1E26"))
        pen.setWidth(2)
        painter.setPen(pen)
        mid_y = size.height() // 2
        painter.drawLine(2, mid_y, size.width() - 2, mid_y)
        painter.end()

    return QIcon(pixmap)
