from __future__ import annotations

from pandaplot.gui.components.common.slider_with_spinbox import SliderWithSpinbox
from PySide6.QtCore import Signal
from PySide6.QtWidgets import QCheckBox, QComboBox, QFormLayout, QLineEdit, QSpinBox, QWidget

from pandaplot_storybook.registry import (
    BoolControl,
    ChoiceControl,
    Control,
    FloatControl,
    IntControl,
    TextControl,
)


class ControlsPanel(QWidget):
    """Renders one labeled editor per Control and reports the live values dict."""

    valuesChanged = Signal(dict)

    def __init__(self, controls: list[Control], parent: QWidget | None = None):
        super().__init__(parent)
        self._values: dict[str, object] = {control.name: control.default for control in controls}
        layout = QFormLayout(self)
        for control in controls:
            layout.addRow(control.name.replace("_", " ").title(), self._build_editor(control))

    def values(self) -> dict[str, object]:
        return dict(self._values)

    def _build_editor(self, control: Control) -> QWidget:
        if isinstance(control, TextControl):
            editor = QLineEdit(control.default)
            editor.textChanged.connect(lambda text: self._set(control.name, text))
            return editor
        if isinstance(control, BoolControl):
            editor = QCheckBox()
            editor.setChecked(control.default)
            editor.toggled.connect(lambda checked: self._set(control.name, checked))
            return editor
        if isinstance(control, ChoiceControl):
            editor = QComboBox()
            editor.addItems(control.options)
            editor.setCurrentText(control.default)
            editor.currentTextChanged.connect(lambda text: self._set(control.name, text))
            return editor
        if isinstance(control, IntControl):
            editor = QSpinBox()
            editor.setRange(control.minimum, control.maximum)
            editor.setValue(control.default)
            editor.valueChanged.connect(lambda value: self._set(control.name, value))
            return editor
        if isinstance(control, FloatControl):
            editor = SliderWithSpinbox(control.minimum, control.maximum)
            editor.setValue(control.default)
            editor.valueChanged.connect(lambda value: self._set(control.name, value))
            return editor
        raise TypeError(f"Unsupported control type: {type(control)!r}")

    def _set(self, name: str, value: object) -> None:
        self._values[name] = value
        self.valuesChanged.emit(self.values())


__all__ = ["ControlsPanel"]
