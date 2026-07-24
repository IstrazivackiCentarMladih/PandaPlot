"""Axes tab: X/Y1/Y2 chip switcher over per-axis scale/limits/ticks/grid forms."""
from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QComboBox,
    QDoubleSpinBox,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from pandaplot.gui.components.common.card import Card
from pandaplot.gui.components.common.chip_row import ChipRow
from pandaplot.gui.components.common.section_header import SectionHeader
from pandaplot.gui.components.common.segmented_control import SegmentedControl
from pandaplot.gui.components.common.toggle_switch import ToggleSwitch
from pandaplot.models.chart.chart_configuration import ScaleType
from pandaplot.models.project.items.chart import YAxis


class AxesTab(QWidget):
    """X/Y1/Y2 chip switcher above a single form area that shows only the
    selected axis's controls.

    Each axis (x, y, y2) gets its own independent set of widgets (built by
    `_build_axis_form_widgets`) rather than one shared form, because (unlike
    the Data/Style tabs' "currently edited series") the three axes are
    genuinely independent, simultaneously-existing config state - nothing
    here is "the currently active axis's data", so there's no shared model
    to reparent a single form around.
    """

    configChanged = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._chart = None
        self._updating_controls = False

        layout = QVBoxLayout(self)

        self.axis_chips = ChipRow()
        self.axis_chips.setItems([("X", "x"), ("Y₁", "y")])
        self.axis_chips.currentValueChanged.connect(self._on_axis_chip_selected)
        layout.addWidget(self.axis_chips)

        self._axis_form_container = QWidget()
        self._axis_form_container_layout = QVBoxLayout(self._axis_form_container)
        self._axis_form_container_layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._axis_form_container)
        layout.addStretch()

        self.axes_forms = {}
        for prefix in ("x", "y", "y2"):
            self._build_axis_form_widgets(prefix)
        self._show_axis_form("x")

    def _build_axis_form_widgets(self, prefix: str):
        """Build one axis's full control set and register it in `self.axes_forms[prefix]`."""
        form_widget = QWidget()
        form_layout = QVBoxLayout(form_widget)
        form_layout.setContentsMargins(0, 0, 0, 0)

        label_row = QHBoxLayout()
        label_row.addWidget(QLabel("Label:"))
        label_edit = QLineEdit()
        label_row.addWidget(label_edit)
        label_row.addWidget(QLabel("Font size:"))
        font_spin = QSpinBox()
        font_spin.setRange(6, 32)
        font_spin.setValue(12)
        label_row.addWidget(font_spin)
        form_layout.addLayout(label_row)

        scale_control = SegmentedControl([("Linear", ScaleType.LINEAR), ("Log", ScaleType.LOG)])
        form_layout.addWidget(scale_control)

        side_control = None
        if prefix in ("y", "y2"):
            side_control = SegmentedControl([("Left", "left"), ("Right", "right")])
            form_layout.addWidget(side_control)

        range_card = Card()
        range_layout = QGridLayout(range_card)
        range_layout.addWidget(SectionHeader("Range"), 0, 0)
        range_layout.addWidget(QLabel("Auto"), 0, 1)
        auto_toggle = ToggleSwitch(checked=True)
        range_layout.addWidget(auto_toggle, 0, 2)
        min_spin = QDoubleSpinBox()
        min_spin.setRange(-1e9, 1e9)
        min_spin.setEnabled(False)
        max_spin = QDoubleSpinBox()
        max_spin.setRange(-1e9, 1e9)
        max_spin.setValue(1.0)
        max_spin.setEnabled(False)
        range_layout.addWidget(QLabel("Min:"), 1, 0)
        range_layout.addWidget(min_spin, 1, 1, 1, 2)
        range_layout.addWidget(QLabel("Max:"), 2, 0)
        range_layout.addWidget(max_spin, 2, 1, 1, 2)
        form_layout.addWidget(range_card)

        ticks_card = Card()
        ticks_layout = QGridLayout(ticks_card)
        ticks_layout.addWidget(SectionHeader("Ticks"), 0, 0, 1, 2)
        mode_control = SegmentedControl([("Auto", "auto"), ("Count", "count"), ("Step", "step")])
        ticks_layout.addWidget(mode_control, 1, 0, 1, 2)
        count_spin = QSpinBox()
        count_spin.setRange(2, 50)
        count_spin.setValue(5)
        count_spin.setEnabled(False)
        step_spin = QDoubleSpinBox()
        step_spin.setRange(0.001, 1e9)
        step_spin.setValue(1.0)
        step_spin.setEnabled(False)
        ticks_layout.addWidget(QLabel("Count:"), 2, 0)
        ticks_layout.addWidget(count_spin, 2, 1)
        ticks_layout.addWidget(QLabel("Step:"), 3, 0)
        ticks_layout.addWidget(step_spin, 3, 1)
        format_combo = QComboBox()
        for text, value in [("Auto", "auto"), ("Integer", "integer"), ("1 Decimal", "1decimal"),
                            ("2 Decimals", "2decimal"), ("Scientific", "scientific"), ("Custom...", "custom")]:
            format_combo.addItem(text, value)
        ticks_layout.addWidget(QLabel("Format:"), 4, 0)
        ticks_layout.addWidget(format_combo, 4, 1)
        format_custom_edit = QLineEdit()
        format_custom_edit.setPlaceholderText("e.g. {:.2f} units")
        format_custom_edit.setEnabled(False)
        ticks_layout.addWidget(format_custom_edit, 5, 0, 1, 2)
        grid_toggle = ToggleSwitch(checked=True)
        ticks_layout.addWidget(QLabel("Show grid"), 6, 0)
        ticks_layout.addWidget(grid_toggle, 6, 1)
        form_layout.addWidget(ticks_card)

        copy_button = None
        if prefix in ("y", "y2"):
            copy_button = QPushButton("Copy settings to Y axis")
            copy_button.setFlat(True)
            copy_button.clicked.connect(lambda _checked=False, p=prefix: self._on_copy_axis_settings(p))
            form_layout.addWidget(copy_button)

        self.axes_forms[prefix] = {
            "widget": form_widget, "label_edit": label_edit, "font_spin": font_spin,
            "scale_control": scale_control, "side_control": side_control,
            "range_card": range_card, "ticks_card": ticks_card,
            "auto_toggle": auto_toggle, "min_spin": min_spin, "max_spin": max_spin,
            "mode_control": mode_control, "count_spin": count_spin, "step_spin": step_spin,
            "format_combo": format_combo, "format_custom_edit": format_custom_edit,
            "grid_toggle": grid_toggle, "copy_button": copy_button,
        }

        # Wire this form's widgets directly to shared handlers - the forms
        # are built dynamically (there are no static self.x_*/self.y_*
        # attributes to hook up elsewhere), so wiring happens here.
        label_edit.textChanged.connect(self._on_field_changed)
        font_spin.valueChanged.connect(self._on_field_changed)
        scale_control.currentValueChanged.connect(self._on_field_changed)
        if side_control is not None:
            side_control.currentValueChanged.connect(self._on_field_changed)
        auto_toggle.toggled.connect(lambda checked, p=prefix: self._on_axis_auto_limits_toggled(p, checked))
        min_spin.valueChanged.connect(self._on_field_changed)
        max_spin.valueChanged.connect(self._on_field_changed)
        mode_control.currentValueChanged.connect(lambda _v, p=prefix: self._on_axis_tick_mode_changed(p))
        count_spin.valueChanged.connect(self._on_field_changed)
        step_spin.valueChanged.connect(self._on_field_changed)
        format_combo.currentIndexChanged.connect(lambda _i, p=prefix: self._on_axis_tick_format_changed(p))
        format_custom_edit.textChanged.connect(self._on_field_changed)
        grid_toggle.toggled.connect(self._on_field_changed)

        form_widget.setVisible(False)
        self._axis_form_container_layout.addWidget(form_widget)

    def _show_axis_form(self, prefix: str):
        """Show only the selected axis's form, hiding the other two."""
        for key, form in self.axes_forms.items():
            form["widget"].setVisible(key == prefix)

    def _on_axis_chip_selected(self, prefix: str):
        self._show_axis_form(prefix)

    def _on_axis_auto_limits_toggled(self, prefix: str, checked: bool):
        form = self.axes_forms[prefix]
        form["min_spin"].setEnabled(not checked)
        form["max_spin"].setEnabled(not checked)
        self._on_field_changed()

    def _on_axis_tick_mode_changed(self, prefix: str):
        form = self.axes_forms[prefix]
        mode = form["mode_control"].currentValue()
        form["count_spin"].setEnabled(mode == "count")
        form["step_spin"].setEnabled(mode == "step")
        self._on_field_changed()

    def _on_axis_tick_format_changed(self, prefix: str):
        form = self.axes_forms[prefix]
        form["format_custom_edit"].setEnabled(form["format_combo"].currentData() == "custom")
        self._on_field_changed()

    def _on_copy_axis_settings(self, prefix: str):
        """Copy the shown Y axis's non-label settings to the other Y axis."""
        other = "y2" if prefix == "y" else "y"
        source = self.axes_forms[prefix]
        target = self.axes_forms[other]

        target["font_spin"].setValue(source["font_spin"].value())
        target["scale_control"].setCurrentValue(source["scale_control"].currentValue())
        if source["side_control"] is not None and target["side_control"] is not None:
            target["side_control"].setCurrentValue(source["side_control"].currentValue())
        target["auto_toggle"].setChecked(source["auto_toggle"].isChecked())
        target["min_spin"].setValue(source["min_spin"].value())
        target["max_spin"].setValue(source["max_spin"].value())
        target["min_spin"].setEnabled(not target["auto_toggle"].isChecked())
        target["max_spin"].setEnabled(not target["auto_toggle"].isChecked())
        target["mode_control"].setCurrentValue(source["mode_control"].currentValue())
        target["count_spin"].setValue(source["count_spin"].value())
        target["step_spin"].setValue(source["step_spin"].value())
        target["count_spin"].setEnabled(target["mode_control"].currentValue() == "count")
        target["step_spin"].setEnabled(target["mode_control"].currentValue() == "step")
        format_index = target["format_combo"].findData(source["format_combo"].currentData())
        if format_index >= 0:
            target["format_combo"].setCurrentIndex(format_index)
        target["format_custom_edit"].setText(source["format_custom_edit"].text())
        target["format_custom_edit"].setEnabled(target["format_combo"].currentData() == "custom")
        target["grid_toggle"].setChecked(source["grid_toggle"].isChecked())

        self._on_field_changed()

    def refresh_axis_chips(self, chart):
        """Sync the Axes tab's chip row with whether any series currently
        uses the secondary Y axis, adding/removing the Y2 chip accordingly.
        Safe to call whenever the chart or its series may have changed
        (chart load, series rebuild) - mirrors `_refresh_style_chips`.

        Public (and takes `chart` explicitly) because the not-yet-migrated
        Data tab (still on `ChartPropertiesPanel`) calls this whenever a
        series' `y_axis` changes.
        """
        self._chart = chart
        has_secondary = bool(chart) and any(
            series.y_axis == YAxis.SECONDARY for series in chart.data_series
        )
        items = [("X", "x"), ("Y₁", "y")]
        if has_secondary:
            items.append(("Y₂", "y2"))
        self.axis_chips.setItems(items)

    def _write_axis_config(self, prefix: str, config: dict):
        """Write one axis form's widget values into `config` (the mutable chart.config dict)."""
        form = self.axes_forms[prefix]
        config[f"{prefix}_label"] = form["label_edit"].text()
        config[f"{prefix}_font_size"] = form["font_spin"].value()
        if form["scale_control"].currentValue():
            config[f"{prefix}_scale"] = form["scale_control"].currentValue().value
        if form["side_control"] is not None:
            config[f"{prefix}_side"] = form["side_control"].currentValue()
        config[f"{prefix}_auto_limits"] = form["auto_toggle"].isChecked()
        config[f"{prefix}_min"] = form["min_spin"].value()
        config[f"{prefix}_max"] = form["max_spin"].value()
        config[f"{prefix}_tick_mode"] = form["mode_control"].currentValue()
        config[f"{prefix}_tick_count"] = form["count_spin"].value()
        config[f"{prefix}_tick_step"] = form["step_spin"].value()
        config[f"{prefix}_tick_format"] = form["format_combo"].currentData()
        config[f"{prefix}_tick_format_custom"] = form["format_custom_edit"].text()
        config[f"show_grid_{prefix}"] = form["grid_toggle"].isChecked()

    def _read_axis_config(self, prefix: str, config: dict):
        """Populate one axis form's widgets from `config`. Assumes the caller
        already has `self._updating_controls` set so change signals don't
        write half-loaded values back out."""
        form = self.axes_forms[prefix]
        form["label_edit"].setText(config.get(f"{prefix}_label", ""))
        form["font_spin"].setValue(config.get(f"{prefix}_font_size", 12))

        scale_value = config.get(f"{prefix}_scale", "linear")
        try:
            form["scale_control"].setCurrentValue(ScaleType(scale_value))
        except ValueError:
            form["scale_control"].setCurrentValue(ScaleType.LINEAR)

        if form["side_control"] is not None:
            default_side = "left" if prefix == "y" else "right"
            form["side_control"].setCurrentValue(config.get(f"{prefix}_side", default_side))

        auto_limits = config.get(f"{prefix}_auto_limits", True)
        form["auto_toggle"].setChecked(auto_limits)
        form["min_spin"].setValue(config.get(f"{prefix}_min", 0.0))
        form["max_spin"].setValue(config.get(f"{prefix}_max", 1.0))
        form["min_spin"].setEnabled(not auto_limits)
        form["max_spin"].setEnabled(not auto_limits)

        tick_mode = config.get(f"{prefix}_tick_mode", "auto")
        form["mode_control"].setCurrentValue(tick_mode)
        form["count_spin"].setValue(config.get(f"{prefix}_tick_count", 5))
        form["step_spin"].setValue(config.get(f"{prefix}_tick_step", 1.0))
        form["count_spin"].setEnabled(tick_mode == "count")
        form["step_spin"].setEnabled(tick_mode == "step")

        tick_format = config.get(f"{prefix}_tick_format", "auto")
        format_index = form["format_combo"].findData(tick_format)
        form["format_combo"].setCurrentIndex(format_index if format_index >= 0 else 0)
        form["format_custom_edit"].setText(config.get(f"{prefix}_tick_format_custom", ""))
        form["format_custom_edit"].setEnabled(tick_format == "custom")

        form["grid_toggle"].setChecked(config.get(f"show_grid_{prefix}", True))

    def _on_field_changed(self):
        if self._chart is None or self._updating_controls:
            return
        config = self._chart.config
        for prefix in ("x", "y", "y2"):
            self._write_axis_config(prefix, config)
        self.configChanged.emit()

    def load(self, chart):
        previous_guard = self._updating_controls
        self._updating_controls = True
        self._chart = chart
        try:
            for prefix in ("x", "y", "y2"):
                self._read_axis_config(prefix, chart.config)
            self.refresh_axis_chips(chart)
            self._show_axis_form("x")
            self.axis_chips.setCurrentValue("x")
        finally:
            self._updating_controls = previous_guard

    def apply_to(self, chart):
        for prefix in ("x", "y", "y2"):
            self._write_axis_config(prefix, chart.config)

    def clear(self):
        self._chart = None
        previous_guard = self._updating_controls
        self._updating_controls = True
        try:
            for prefix in ("x", "y", "y2"):
                self._read_axis_config(prefix, {})
            self.refresh_axis_chips(None)
        finally:
            self._updating_controls = previous_guard

    def apply_theme(self, tokens: dict):
        self.axis_chips.set_tokens(tokens)
        for form in self.axes_forms.values():
            form["scale_control"].set_tokens(tokens)
            if form["side_control"] is not None:
                form["side_control"].set_tokens(tokens)
            form["range_card"].set_tokens(tokens)
            form["ticks_card"].set_tokens(tokens)
            form["mode_control"].set_tokens(tokens)
            form["auto_toggle"].set_tokens(tokens)
            form["grid_toggle"].set_tokens(tokens)
