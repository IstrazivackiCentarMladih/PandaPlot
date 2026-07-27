"""Legend tab: chart legend visibility, position, columns, frame, background."""
from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QComboBox,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from pandaplot.gui.components.common.card import Card
from pandaplot.gui.components.common.color_swatch_row import ColorSwatchRow
from pandaplot.gui.components.common.section_header import SectionHeader
from pandaplot.gui.components.common.segmented_control import SegmentedControl
from pandaplot.gui.components.common.slider_with_spinbox import SliderWithSpinbox
from pandaplot.gui.components.common.toggle_switch import ToggleSwitch
from pandaplot.models.chart.chart_configuration import LegendPosition


class LegendTab(QWidget):
    """Legend visibility/position/frame/background configuration."""

    configChanged = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._chart = None
        self._updating_controls = False

        layout = QVBoxLayout(self)

        show_row = QHBoxLayout()
        show_row.addWidget(QLabel("Show legend"))
        self.show_legend_toggle = ToggleSwitch(checked=True)
        show_row.addWidget(self.show_legend_toggle)
        show_row.addStretch(1)
        layout.addLayout(show_row)

        legend_group = QGroupBox("Legend")
        legend_layout = QGridLayout(legend_group)

        legend_layout.addWidget(QLabel("Position:"), 0, 0)
        self.legend_position_combo = QComboBox()
        for position in LegendPosition:
            self.legend_position_combo.addItem(position.value.title(), position)
        legend_layout.addWidget(self.legend_position_combo, 0, 1)

        legend_layout.addWidget(QLabel("Font Size:"), 1, 0)
        self.legend_font_size_spin = QSpinBox()
        self.legend_font_size_spin.setRange(6, 18)
        self.legend_font_size_spin.setValue(10)
        legend_layout.addWidget(self.legend_font_size_spin, 1, 1)

        legend_layout.addWidget(QLabel("Columns:"), 2, 0)
        self.legend_columns_control = SegmentedControl([("1", 1), ("2", 2), ("3", 3)])
        legend_layout.addWidget(self.legend_columns_control, 2, 1)

        layout.addWidget(legend_group)

        frame_card = Card()
        frame_layout = QGridLayout(frame_card)
        frame_layout.addWidget(SectionHeader("Frame"), 0, 0)
        self.legend_show_frame_toggle = ToggleSwitch(checked=True)
        frame_layout.addWidget(self.legend_show_frame_toggle, 0, 1)
        frame_layout.addWidget(QLabel("Background:"), 1, 0)
        self.legend_bg_color_row = ColorSwatchRow(["#FFFFFF", "#F4F5F8", "#1C1E26"])
        frame_layout.addWidget(self.legend_bg_color_row, 1, 1)
        frame_layout.addWidget(QLabel("Opacity:"), 2, 0)
        self.legend_bg_opacity_slider = SliderWithSpinbox(minimum=0.0, maximum=1.0, decimals=2)
        frame_layout.addWidget(self.legend_bg_opacity_slider, 2, 1)
        layout.addWidget(frame_card)

        layout.addStretch()

        self.show_legend_toggle.toggled.connect(self._on_show_legend_toggled)
        self.legend_position_combo.currentIndexChanged.connect(self._on_field_changed)
        self.legend_font_size_spin.valueChanged.connect(self._on_field_changed)
        self.legend_columns_control.currentValueChanged.connect(self._on_field_changed)
        self.legend_show_frame_toggle.toggled.connect(self._on_field_changed)
        self.legend_bg_color_row.colorChanged.connect(self._on_field_changed)
        self.legend_bg_opacity_slider.valueChanged.connect(self._on_field_changed)

    def _on_show_legend_toggled(self, _checked: bool):
        self._update_legend_controls_enabled()
        self._on_field_changed()

    def _update_legend_controls_enabled(self):
        """Enable/disable every other Legend-tab widget based on the master toggle."""
        show_legend = self.show_legend_toggle.isChecked()
        for control in (
            self.legend_position_combo,
            self.legend_font_size_spin,
            self.legend_columns_control,
            self.legend_show_frame_toggle,
            self.legend_bg_color_row,
            self.legend_bg_opacity_slider,
        ):
            control.setEnabled(show_legend)

    def _on_field_changed(self):
        if self._chart is None or self._updating_controls:
            return
        config = self._chart.config
        config["show_legend"] = self.show_legend_toggle.isChecked()
        if self.legend_position_combo.currentData():
            config["legend_position"] = self.legend_position_combo.currentData().value
        config["legend_font_size"] = self.legend_font_size_spin.value()
        config["legend_columns"] = self.legend_columns_control.currentValue()
        config["legend_show_frame"] = self.legend_show_frame_toggle.isChecked()
        config["legend_bg_color"] = self.legend_bg_color_row.currentColor()
        config["legend_bg_alpha"] = self.legend_bg_opacity_slider.value()
        self.configChanged.emit()

    def load(self, chart):
        previous_guard = self._updating_controls
        self._updating_controls = True
        self._chart = chart
        try:
            config = chart.config
            self.show_legend_toggle.setChecked(config.get("show_legend", True))
            legend_position_value = config.get("legend_position", "upper right")
            for i in range(self.legend_position_combo.count()):
                if (self.legend_position_combo.itemData(i)
                        and self.legend_position_combo.itemData(i).value == legend_position_value):
                    self.legend_position_combo.setCurrentIndex(i)
                    break
            self.legend_font_size_spin.setValue(config.get("legend_font_size", 10))
            self.legend_columns_control.setCurrentValue(config.get("legend_columns", 1))
            self.legend_show_frame_toggle.setChecked(config.get("legend_show_frame", True))
            self.legend_bg_color_row.setCurrentColor(config.get("legend_bg_color", "#ffffff"))
            self.legend_bg_opacity_slider.setValue(config.get("legend_bg_alpha", 1.0))
            self._update_legend_controls_enabled()
        finally:
            self._updating_controls = previous_guard

    def apply_to(self, chart):
        chart.config["show_legend"] = self.show_legend_toggle.isChecked()
        if self.legend_position_combo.currentData():
            chart.config["legend_position"] = self.legend_position_combo.currentData().value
        chart.config["legend_font_size"] = self.legend_font_size_spin.value()
        chart.config["legend_columns"] = self.legend_columns_control.currentValue()
        chart.config["legend_show_frame"] = self.legend_show_frame_toggle.isChecked()
        chart.config["legend_bg_color"] = self.legend_bg_color_row.currentColor()
        chart.config["legend_bg_alpha"] = self.legend_bg_opacity_slider.value()

    def clear(self):
        self._chart = None
        previous_guard = self._updating_controls
        self._updating_controls = True
        try:
            self.show_legend_toggle.setChecked(True)
            self.legend_columns_control.setCurrentValue(1)
            self.legend_show_frame_toggle.setChecked(True)
            self.legend_bg_color_row.setCurrentColor("#ffffff")
            self.legend_bg_opacity_slider.setValue(1.0)
            self._update_legend_controls_enabled()
        finally:
            self._updating_controls = previous_guard

    def apply_theme(self, tokens: dict):
        self.show_legend_toggle.set_tokens(tokens)
        self.legend_columns_control.set_tokens(tokens)
        self.legend_show_frame_toggle.set_tokens(tokens)
        self.legend_bg_color_row.set_tokens(tokens)
        self.legend_bg_opacity_slider.set_tokens(tokens)
