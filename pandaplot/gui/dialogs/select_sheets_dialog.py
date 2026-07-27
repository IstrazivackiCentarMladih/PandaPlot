"""Dialog for choosing which sheet(s) of a multi-sheet Excel workbook to import."""

from typing import List, Optional, override

from PySide6.QtWidgets import (
    QCheckBox,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from pandaplot.gui.core.widget_extension import PDialog
from pandaplot.services.theme.theme_manager import ThemeManager


class SelectSheetsDialog(PDialog):
    """Lets the user choose which sheet(s) of an Excel workbook to import.

    Each selected sheet becomes its own Dataset. On acceptance,
    `selected_sheets` holds the chosen sheet names in workbook order;
    it stays None if the dialog was cancelled.
    """

    def __init__(self, app_context, sheet_names: List[str], parent=None):
        super().__init__(app_context=app_context, parent=parent)
        self._sheet_names = sheet_names
        self._checkboxes: List[QCheckBox] = []
        self.selected_sheets: Optional[List[str]] = None
        self._initialize()

    @override
    def _init_ui(self):
        self.setWindowTitle("Select Sheets to Import")
        self.setModal(True)
        self.resize(360, 420)
        self.setMinimumSize(300, 260)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(10)

        self.title_label = QLabel("This workbook has multiple sheets.")
        title_font = self.title_label.font()
        title_font.setBold(True)
        self.title_label.setFont(title_font)
        layout.addWidget(self.title_label)

        self.subtitle_label = QLabel("Choose which sheet(s) to import as datasets:")
        layout.addWidget(self.subtitle_label)

        buttons_row = QHBoxLayout()
        select_all_btn = QPushButton("Select All")
        select_all_btn.clicked.connect(lambda: self._set_all_checked(True))
        deselect_all_btn = QPushButton("Deselect All")
        deselect_all_btn.clicked.connect(lambda: self._set_all_checked(False))
        buttons_row.addWidget(select_all_btn)
        buttons_row.addWidget(deselect_all_btn)
        buttons_row.addStretch()
        layout.addLayout(buttons_row)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        list_widget = QWidget()
        self.list_layout = QVBoxLayout(list_widget)
        self.list_layout.setContentsMargins(0, 0, 0, 0)
        for sheet_name in self._sheet_names:
            checkbox = QCheckBox(sheet_name)
            checkbox.setChecked(True)  # default to importing every sheet
            self._checkboxes.append(checkbox)
            self.list_layout.addWidget(checkbox)
        self.list_layout.addStretch()
        scroll_area.setWidget(list_widget)
        layout.addWidget(scroll_area, 1)

        self.button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.button_box.accepted.connect(self._on_accept)
        self.button_box.rejected.connect(self.reject)
        layout.addWidget(self.button_box)

    def _set_all_checked(self, checked: bool):
        for checkbox in self._checkboxes:
            checkbox.setChecked(checked)

    def _on_accept(self):
        selected = [checkbox.text() for checkbox in self._checkboxes if checkbox.isChecked()]
        if not selected:
            self.subtitle_label.setText("Choose which sheet(s) to import as datasets: (select at least one)")
            return
        self.selected_sheets = selected
        self.accept()

    @override
    def _apply_theme(self):
        theme_manager = self.app_context.get_manager(ThemeManager)
        palette = theme_manager.get_surface_palette()

        card_bg = palette.get("card_bg", "#f8f9fa")
        base_fg = palette.get("base_fg", "#000000")
        secondary_fg = palette.get("secondary_fg", "#555555")
        card_border = palette.get("card_border", "#dee2e6")

        self.setStyleSheet(f"""
            QDialog {{
                background-color: {card_bg};
                color: {base_fg};
            }}
            QLabel {{
                color: {base_fg};
            }}
            QCheckBox {{
                color: {base_fg};
            }}
            QScrollArea {{
                border: 1px solid {card_border};
            }}
        """)
        self.subtitle_label.setStyleSheet(f"color: {secondary_fg};")
