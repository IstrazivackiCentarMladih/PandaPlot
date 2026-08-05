"""Shared step-rail widget for the chart creation wizard: a numbered-circle
row with connecting lines, showing the current step, completed steps (with
a clickable summary of what was chosen), and upcoming steps.

Each `ChartWizard` page owns its own `WizardStepRail` instance -- `QWizard`
swaps whole page widgets on navigation, so there's no single persistent
chrome region to share one instance through. `ChartWizard._on_page_changed`
keeps every page's rail in sync by calling `set_state` on whichever page is
current.
"""
from PySide6.QtCore import Signal
from PySide6.QtWidgets import QFrame, QHBoxLayout, QPushButton, QWidget


class WizardStepRail(QWidget):
    """Numbered-circle step row. `steps[i]` is the label for step `i`."""

    stepClicked = Signal(int)

    def __init__(self, steps: list[str], parent: QWidget | None = None):
        super().__init__(parent)
        if not steps:
            raise ValueError("WizardStepRail requires at least one step")
        self._steps = steps
        self._tokens: dict = {}
        self._step_widgets: list[QPushButton] = []
        self._connectors: list[QFrame] = []

        self._layout = QHBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(8)

        for i, label in enumerate(steps):
            button = QPushButton(label, self)
            button.setFlat(True)
            button.clicked.connect(lambda _checked=False, idx=i: self._on_step_clicked(idx))
            self._layout.addWidget(button)
            self._step_widgets.append(button)
            if i < len(steps) - 1:
                connector = QFrame(self)
                connector.setFrameShape(QFrame.Shape.HLine)
                self._layout.addWidget(connector, 1)
                self._connectors.append(connector)

        self.set_state(current_index=0, summaries={})

    def _on_step_clicked(self, index: int):
        if index < self._current_index:
            self.stepClicked.emit(index)

    def set_state(self, current_index: int, summaries: dict[int, str]) -> None:
        """`summaries` maps a *completed* step's index (< current_index) to
        the "Label · chosen value" text its button should show. Steps with no
        entry keep their plain label."""
        self._current_index = current_index
        for i, button in enumerate(self._step_widgets):
            if i < current_index:
                button.setText(summaries.get(i, self._steps[i]))
                button.setEnabled(True)
                button.setProperty("stepState", "completed")
            elif i == current_index:
                button.setText(self._steps[i])
                button.setEnabled(False)
                button.setProperty("stepState", "current")
            else:
                button.setText(self._steps[i])
                button.setEnabled(False)
                button.setProperty("stepState", "upcoming")
        self._apply_styles()

    def set_tokens(self, tokens: dict) -> None:
        self._tokens = tokens
        self._apply_styles()

    def _apply_styles(self) -> None:
        accent = self._tokens.get("accent", "#4A56C6")
        muted = self._tokens.get("text_muted", "#9AA0AB")
        text_primary = self._tokens.get("text_primary", "#1C1E26")
        border = self._tokens.get("border_control", "#DCDEE4")
        for button in self._step_widgets:
            state = button.property("stepState")
            if state == "current":
                style = f"font-weight: 700; color: {accent}; border: none;"
            elif state == "completed":
                style = f"font-weight: 600; color: {text_primary}; border: none;"
            else:
                style = f"color: {muted}; border: none;"
            button.setStyleSheet(f"QPushButton {{ {style} }}")
        for connector in self._connectors:
            connector.setStyleSheet(f"background-color: {border};")
