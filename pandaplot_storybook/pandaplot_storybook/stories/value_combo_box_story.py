from __future__ import annotations

from pandaplot.gui.components.common.value_combo_box import ValueComboBox
from PySide6.QtWidgets import QWidget

from pandaplot_storybook.registry import ChoiceControl, StoryDef, story

_OPTIONS = ["One", "Two", "Three"]


@story("ValueComboBox")
def _build() -> StoryDef:
    def make_widget(values: dict, tokens: dict) -> QWidget:
        widget = ValueComboBox([(label, label) for label in _OPTIONS])
        widget.setCurrentValue(values["selected"])
        return widget

    return StoryDef(controls=[ChoiceControl("selected", _OPTIONS[0], _OPTIONS)], make_widget=make_widget)
