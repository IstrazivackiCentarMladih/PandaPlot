"""Floating bar that lets the chart wizard borrow column-header clicks from
a live dataset tab while staying open behind it.

The wizard is normally application-modal. Picking a column from the real
dataset table (rather than a dropdown) requires the main window to be
interactive, so `start()` temporarily drops the wizard to non-modal, opens/
focuses the target dataset's tab via `TabContainer`, and tracks that tab's
column selection live. Calling `_finish()` (wired to the bar's "Done"
button) restores the wizard's modal state and hands the picked column ids
back to the caller.
"""
import logging
from typing import Callable, Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QHBoxLayout, QLabel, QPushButton, QWidget

from pandaplot.gui.components.tabs.tab_container import TabContainer
from pandaplot.models.state.app_context import AppContext

logger = logging.getLogger(__name__)


class DatasetColumnPicker(QWidget):
    """A floating 'Picking for: <role> — <preview> — [Done]' bar."""

    def __init__(self, app_context: AppContext, parent: Optional[QWidget] = None):
        super().__init__(parent, Qt.WindowType.Tool | Qt.WindowType.FramelessWindowHint)
        self.app_context = app_context
        self._wizard: Optional[QDialog] = None
        self._table_view = None
        self._role_label: str = ""
        self._on_done: Optional[Callable[[list[str]], None]] = None

        layout = QHBoxLayout(self)
        self._label = QLabel()
        layout.addWidget(self._label, 1)
        self._done_button = QPushButton("Done")
        self._done_button.clicked.connect(self._finish)
        layout.addWidget(self._done_button)

    def start(self, wizard: QDialog, dataset_id: str, role_label: str,
              on_done: Callable[[list[str]], None]) -> None:
        """Arm picking for `role_label` on `dataset_id`, borrowing the main window."""
        if self._table_view is not None:
            self._table_view.selectionModel().selectionChanged.disconnect(self._on_selection_changed)
            self._table_view = None

        self._wizard = wizard
        self._role_label = role_label
        self._on_done = on_done

        tab_container = self.app_context.get_manager(TabContainer)
        tab_container.open_tab(dataset_id)
        dataset_tab = tab_container.get_tab_widget(dataset_id)
        self._table_view = getattr(dataset_tab, "table_view", None)
        if self._table_view is not None:
            self._table_view.selectionModel().selectionChanged.connect(self._on_selection_changed)

        self._update_label()
        wizard.setWindowModality(Qt.WindowModality.NonModal)
        wizard.hide()
        wizard.show()
        self.move(wizard.geometry().topLeft())
        self.show()
        self.raise_()

    def _on_selection_changed(self, *_args) -> None:
        self._update_label()

    def _update_label(self) -> None:
        names = self._selected_column_names()
        preview = ", ".join(names) if names else "no column selected"
        self._label.setText(f"Picking for: {self._role_label} — {preview}")

    def _selected_column_names(self) -> list[str]:
        if self._table_view is None:
            return []
        dataset = self._table_view.model()._dataset
        columns = list(dataset.data.columns)
        selected = self._table_view.selectionModel().selectedColumns()
        return [columns[index.column()] for index in selected if index.column() < len(columns)]

    def _selected_column_ids(self) -> list[str]:
        if self._table_view is None:
            return []
        dataset = self._table_view.model()._dataset
        ids: list[str] = []
        for name in self._selected_column_names():
            column_id = dataset.column_id(name)
            if column_id:
                ids.append(column_id)
            else:
                logger.warning(
                    "Selected column %r did not resolve to a stable column id; excluding it from the picker result.",
                    name,
                )
        return ids

    def _finish(self) -> None:
        if self._table_view is not None:
            self._table_view.selectionModel().selectionChanged.disconnect(self._on_selection_changed)
        column_ids = self._selected_column_ids()
        self.hide()
        if self._wizard is not None:
            self._wizard.setWindowModality(Qt.WindowModality.ApplicationModal)
            self._wizard.show()
            self._wizard.raise_()
        if self._on_done is not None:
            self._on_done(column_ids)
