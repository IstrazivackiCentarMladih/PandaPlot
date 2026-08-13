from __future__ import annotations

from pandaplot.gui.components.common.segmented_control import SegmentedControl
from PySide6.QtWidgets import QWidget

from pandaplot_storybook.registry import ChoiceControl, StoryDef, story

_OPTIONS = ["Day", "Week", "Month"]


@story("SegmentedControl")
def _build() -> StoryDef:
    def make_widget(values: dict, tokens: dict) -> QWidget:
        widget = SegmentedControl([(label, label) for label in _OPTIONS])
        widget.setCurrentValue(values["selected"])
        return widget

    return StoryDef(controls=[ChoiceControl("selected", _OPTIONS[0], _OPTIONS)], make_widget=make_widget)
