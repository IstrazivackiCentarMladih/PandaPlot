from __future__ import annotations

from pandaplot.gui.components.common.font_family_options import list_available_font_families
from PySide6.QtWidgets import QListWidget, QWidget

from pandaplot_storybook.registry import StoryDef, story


@story("FontFamilyOptions")
def _build() -> StoryDef:
    def make_widget(values: dict, tokens: dict) -> QWidget:
        gallery = QListWidget()
        gallery.addItems([label for label, _value in list_available_font_families()])
        return gallery

    return StoryDef(controls=[], make_widget=make_widget)
