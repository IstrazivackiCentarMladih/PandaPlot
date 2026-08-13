from __future__ import annotations

from pandaplot.gui.components.common.chip_row import ChipRow
from PySide6.QtWidgets import QWidget

from pandaplot_storybook.registry import ChoiceControl, StoryDef, story

_OPTIONS = ["Series A", "Series B", "Series C"]


@story("ChipRow")
def _build() -> StoryDef:
    def make_widget(values: dict, tokens: dict) -> QWidget:
        widget = ChipRow()
        widget.setItems([(label, label) for label in _OPTIONS])
        widget.setCurrentValue(values["selected"])
        return widget

    return StoryDef(controls=[ChoiceControl("selected", _OPTIONS[0], _OPTIONS)], make_widget=make_widget)
