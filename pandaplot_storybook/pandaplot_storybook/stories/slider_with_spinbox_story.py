from __future__ import annotations

from pandaplot.gui.components.common.slider_with_spinbox import SliderWithSpinbox
from PySide6.QtWidgets import QWidget

from pandaplot_storybook.registry import FloatControl, StoryDef, story


@story("SliderWithSpinbox")
def _build() -> StoryDef:
    def make_widget(values: dict, tokens: dict) -> QWidget:
        widget = SliderWithSpinbox(0.0, 10.0, decimals=1)
        widget.setValue(values["value"])
        return widget

    return StoryDef(controls=[FloatControl("value", 5.0, 0.0, 10.0)], make_widget=make_widget)
