from __future__ import annotations

from pandaplot.gui.components.common.section_header import SectionHeader
from PySide6.QtWidgets import QWidget

from pandaplot_storybook.registry import StoryDef, TextControl, story


@story("SectionHeader")
def _build() -> StoryDef:
    def make_widget(values: dict, tokens: dict) -> QWidget:
        return SectionHeader(values["text"])

    return StoryDef(controls=[TextControl("text", "Series")], make_widget=make_widget)
