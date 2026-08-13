from __future__ import annotations

from pandaplot.gui.components.common.line_style_icons import build_line_style_icon
from pandaplot.models.chart.chart_configuration import LineStyleType
from PySide6.QtWidgets import QListWidget, QListWidgetItem, QWidget

from pandaplot_storybook.registry import StoryDef, story


class _LineStyleGallery(QListWidget):
    """Read-only gallery of every LineStyleType's drawn icon.

    build_line_style_icon() bakes the current design tokens into the drawn
    pixmap, so this exposes set_tokens() (rather than relying on global QSS)
    to redraw with fresh colors whenever MainWindow's theme switch fires.
    """

    def set_tokens(self, tokens: dict) -> None:
        self.clear()
        for line_style in LineStyleType:
            self.addItem(QListWidgetItem(build_line_style_icon(line_style, tokens), line_style.value))


@story("LineStyleIcons")
def _build() -> StoryDef:
    def make_widget(values: dict, tokens: dict) -> QWidget:
        gallery = _LineStyleGallery()
        gallery.set_tokens(tokens)
        return gallery

    return StoryDef(controls=[], make_widget=make_widget)
