from __future__ import annotations

from pandaplot.gui.components.common.drop_down_combo_box import DropDownComboBox
from PySide6.QtWidgets import QWidget

from pandaplot_storybook.registry import ChoiceControl, StoryDef, story

_OPTIONS = ["Alpha", "Beta", "Gamma"]


@story("DropDownComboBox")
def _build() -> StoryDef:
    def make_widget(values: dict, tokens: dict) -> QWidget:
        widget = DropDownComboBox()
        widget.addItems(_OPTIONS)
        widget.setCurrentText(values["selected"])
        return widget

    return StoryDef(controls=[ChoiceControl("selected", _OPTIONS[0], _OPTIONS)], make_widget=make_widget)
