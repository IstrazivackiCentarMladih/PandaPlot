"""One series' configuration card for the chart creation wizard's Data step:
dataset picker, per-role column pickers (+ 'pick from dataset' buttons),
an optional error-bars toggle, and a remove button.
"""
from typing import Optional

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QWidget,
)

from pandaplot.gui.dialogs.chart.chart_role_spec import ChartRoleSpec

_ROLE_LABELS = {"x": "X column", "y": "Y column", "values": "Values column"}
_ROLE_TO_FIELD = {"x": "x_column_id", "y": "y_column_id", "values": "y_column_id"}


class SeriesConfigCard(QWidget):
    removeRequested = Signal()
    pickRequested = Signal(str)
    configChanged = Signal()
    datasetChanged = Signal(str)

    def __init__(self, role_spec: ChartRoleSpec, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._role_spec = role_spec
        self._role_combos: dict[str, QComboBox] = {}
        self.error_bars_check: Optional[QCheckBox] = None
        self.x_error_column_combo: Optional[QComboBox] = None
        self.y_error_column_combo: Optional[QComboBox] = None
        self._build_ui()

    def _build_ui(self):
        grid = QGridLayout(self)
        row = 0

        grid.addWidget(QLabel("Dataset:"), row, 0)
        self.dataset_combo = QComboBox()
        self.dataset_combo.currentIndexChanged.connect(self._on_dataset_changed)
        grid.addWidget(self.dataset_combo, row, 1)
        row += 1

        for role in self._role_spec.roles:
            grid.addWidget(QLabel(f"{_ROLE_LABELS[role]}:"), row, 0)
            combo = QComboBox()
            combo.currentIndexChanged.connect(lambda _index=None: self.configChanged.emit())
            self._role_combos[role] = combo
            setattr(self, f"{role}_column_combo", combo)
            role_row = QHBoxLayout()
            role_row.addWidget(combo, 1)
            pick_button = QPushButton("Pick from dataset")
            pick_button.clicked.connect(lambda _checked=False, r=role: self.pickRequested.emit(r))
            setattr(self, f"{role}_pick_button", pick_button)
            role_row.addWidget(pick_button, 0)
            grid.addLayout(role_row, row, 1)
            row += 1

        if self._role_spec.supports_error_bars:
            self.error_bars_check = QCheckBox("Add error bars")
            self.error_bars_check.toggled.connect(self._on_error_bars_toggled)
            grid.addWidget(self.error_bars_check, row, 0, 1, 2)
            row += 1

            for error_role, label in (("x_error", "X error column"), ("y_error", "Y error column")):
                error_label = QLabel(f"{label}:")
                combo = QComboBox()
                combo.currentIndexChanged.connect(lambda _index=None: self.configChanged.emit())
                self._role_combos[error_role] = combo
                setattr(self, f"{error_role}_column_combo", combo)
                error_row = QHBoxLayout()
                error_row.addWidget(combo, 1)
                pick_button = QPushButton("Pick from dataset")
                pick_button.clicked.connect(lambda _checked=False, r=error_role: self.pickRequested.emit(r))
                error_row.addWidget(pick_button, 0)
                grid.addWidget(error_label, row, 0)
                grid.addLayout(error_row, row, 1)
                setattr(self, f"_{error_role}_label", error_label)
                setattr(self, f"_{error_role}_row", error_row)
                row += 1

            self._set_error_controls_visible(False)

        self.remove_button = QPushButton("Remove")
        self.remove_button.clicked.connect(self.removeRequested.emit)
        grid.addWidget(self.remove_button, row, 0, 1, 2)

    def _set_error_controls_visible(self, visible: bool):
        for error_role in ("x_error", "y_error"):
            getattr(self, f"_{error_role}_label").setVisible(visible)
            combo = self._role_combos[error_role]
            combo.setVisible(visible)
            for i in range(getattr(self, f"_{error_role}_row").count()):
                item = getattr(self, f"_{error_role}_row").itemAt(i)
                if item.widget() is not None:
                    item.widget().setVisible(visible)

    def _on_error_bars_toggled(self, checked: bool):
        self._set_error_controls_visible(checked)
        self.configChanged.emit()

    def _on_dataset_changed(self):
        dataset_id = self.dataset_combo.currentData()
        if dataset_id:
            self.datasetChanged.emit(dataset_id)
        self.configChanged.emit()

    def set_datasets(self, datasets: list[tuple[str, str]]) -> None:
        """`datasets` is a list of (dataset_id, display_name)."""
        self.dataset_combo.blockSignals(True)
        try:
            self.dataset_combo.clear()
            for dataset_id, name in datasets:
                self.dataset_combo.addItem(name, dataset_id)
        finally:
            self.dataset_combo.blockSignals(False)

    def set_dataset_columns(self, dataset_id: str, columns: list[tuple[str, str]]) -> None:
        """`columns` is a list of (column_id, display_name) for `dataset_id`.

        Populates every role combo (including error-column combos) the same
        way; a no-op if `dataset_id` isn't the currently selected dataset.
        """
        if self.dataset_combo.currentData() != dataset_id:
            return
        for combo in self._role_combos.values():
            combo.blockSignals(True)
            try:
                combo.clear()
                combo.addItem("", "")
                for column_id, name in columns:
                    combo.addItem(name, column_id)
            finally:
                combo.blockSignals(False)

    def get_series_config(self) -> dict:
        config = {
            "dataset_id": self.dataset_combo.currentData() or "",
            "x_column_id": "",
            "y_column_id": "",
            "x_error_column_id": "",
            "y_error_column_id": "",
            "error_symmetric": True,
        }
        for role in self._role_spec.roles:
            config[_ROLE_TO_FIELD[role]] = self._role_combos[role].currentData() or ""
        if self.error_bars_check is not None and self.error_bars_check.isChecked():
            config["x_error_column_id"] = self._role_combos["x_error"].currentData() or ""
            config["y_error_column_id"] = self._role_combos["y_error"].currentData() or ""
        return config

    def get_display_names(self) -> dict[str, str]:
        """Display names (not ids) for roles that currently have a selection.

        Mirrors `get_series_config()`'s role handling but returns the combo's
        current text instead of its id -- used only to seed human-readable
        defaults (e.g. axis-label suggestions in the wizard's Labels step),
        never as a source of truth for a persisted column reference.
        """
        names: dict[str, str] = {}
        for role in self._role_spec.roles:
            combo = self._role_combos[role]
            if combo.currentData():
                names[role] = combo.currentText()
        return names

    def is_complete(self) -> bool:
        if not self.dataset_combo.currentData():
            return False
        for role in self._role_spec.required_roles:
            if not self._role_combos[role].currentData():
                return False
        return True

    def apply_picked_columns(self, role: str, column_ids: list[str]) -> None:
        if not column_ids or role not in self._role_combos:
            return
        combo = self._role_combos[role]
        index = combo.findData(column_ids[0])
        if index >= 0:
            combo.setCurrentIndex(index)
