from __future__ import annotations

from pandaplot.gui.components.common.dirty_footer import DirtyFooter
from PySide6.QtWidgets import QWidget

from pandaplot_storybook.registry import BoolControl, IntControl, StoryDef, story


@story("DirtyFooter")
def _build() -> StoryDef:
    def make_widget(values: dict, tokens: dict) -> QWidget:
        widget = DirtyFooter()
        widget.setModified(values["modified"], values["change_count"])
        return widget

    return StoryDef(
        controls=[BoolControl("modified", True), IntControl("change_count", 3, 0, 20)],
        make_widget=make_widget,
    )
