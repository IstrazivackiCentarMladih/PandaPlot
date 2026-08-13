from __future__ import annotations

from pandaplot.gui.components.common.card import Card
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

from pandaplot_storybook.registry import StoryDef, TextControl, story


@story("Card")
def _build() -> StoryDef:
    def make_widget(values: dict, tokens: dict) -> QWidget:
        card = Card()
        layout = QVBoxLayout(card)
        layout.addWidget(QLabel(values["label"]))
        return card

    return StoryDef(controls=[TextControl("label", "Card content")], make_widget=make_widget)
