from __future__ import annotations

from pandaplot.gui.components.common.color_swatch_row import ColorSwatchRow
from PySide6.QtWidgets import QWidget

from pandaplot_storybook.registry import ChoiceControl, StoryDef, story

_PALETTE = ["#4A56C6", "#DC3545", "#3FA46A", "#E09A1F"]


@story("ColorSwatchRow")
def _build() -> StoryDef:
    def make_widget(values: dict, tokens: dict) -> QWidget:
        widget = ColorSwatchRow(list(_PALETTE))
        widget.setCurrentColor(values["current_color"])
        return widget

    return StoryDef(controls=[ChoiceControl("current_color", _PALETTE[0], _PALETTE)], make_widget=make_widget)
