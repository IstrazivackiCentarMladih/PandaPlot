"""Floating bar that lets the chart wizard borrow column-header clicks from
a live dataset tab while staying open behind it.

The wizard is normally application-modal. Picking a column from the real
dataset table (rather than a dropdown) requires the main window to be
interactive, so `start()` temporarily drops the wizard to non-modal, shrinks
it in place to a small floating bar, opens/focuses the target dataset's tab
via `TabContainer`, and tracks that tab's column selection live. Calling
`_finish()` (wired to the bar's "Done" button) restores the wizard's modal
state and geometry and hands the picked column ids back to the caller.

IMPORTANT: `start()`/`_finish()` must perform a real
hide -> setWindowModality() -> show cycle on the wizard. Qt only updates a
window's modal-blocking registration on `show()`/`hide()`; calling
`setWindowModality()` on an already-visible window is a documented no-op until
the next hide/show cycle. Without the cycle the main window stays blocked and
dataset column clicks are swallowed — and a wizard closed mid-session stays
registered as blocking-but-nonmodal, freezing all input.

This is safe because `CreateChartFromWizardCommand` opens the wizard with
`show()` (non-blocking) and reacts to its `finished(int)` signal — there is no
`exec()` event loop for `hide()` to tear down.
"""
from typing import Callable, Optional

from PySide6.QtCore import QRect, Qt
from PySide6.QtWidgets import QDialog, QHBoxLayout, QLabel, QPushButton, QWidget

from pandaplot.gui.components.tabs.tab_container import TabContainer
from pandaplot.models.state.app_context import AppContext


class DatasetColumnPicker(QWidget):
    """A floating 'Picking for: <role> — <preview> — [Done]' bar."""

    def __init__(self, app_context: AppContext, parent: Optional[QWidget] = None):
        super().__init__(parent, Qt.WindowType.Tool | Qt.WindowType.FramelessWindowHint)
        self.app_context = app_context
        self._wizard: Optional[QDialog] = None
        self._table_view = None
        self._role_label: str = ""
        self._on_done: Optional[Callable[[list[str]], None]] = None
        self._wizard_previous_modality: Qt.WindowModality = Qt.WindowModality.ApplicationModal
        self._wizard_previous_geometry: Optional[QRect] = None

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
        self._wizard_previous_modality = wizard.windowModality()
        self._wizard_previous_geometry = QRect(wizard.geometry())

        tab_container = self.app_context.get_manager(TabContainer)
        tab_container.open_tab(dataset_id)
        dataset_tab = tab_container.get_tab_widget(dataset_id)
        self._table_view = getattr(dataset_tab, "table_view", None)
        if self._table_view is not None:
            self._table_view.selectionModel().selectionChanged.connect(self._on_selection_changed)

        self._update_label()
        # A real hide -> change modality -> show cycle: Qt only updates a
        # window's modal-blocking registration on show()/hide(), so this is the
        # only way `NonModal` actually takes effect and unblocks the main
        # window's input. Safe now because the wizard is shown via `show()`
        # (see CreateChartFromWizardCommand), not a blocking `exec()` call --
        # hiding it here does not tear down any event loop.
        top_left = self._wizard_previous_geometry.topLeft()
        wizard.hide()
        wizard.setWindowModality(Qt.WindowModality.NonModal)
        wizard.setGeometry(top_left.x(), top_left.y(), 420, 90)
        wizard.show()
        self.move(top_left.x(), top_left.y() + 100)
        self.show()
        self.raise_()

    def _on_selection_changed(self, *_args) -> None:
        self._update_label()

    def _update_label(self) -> None:
        names = self._selected_column_names()
        preview = ", ".join(names) if names else "no column selected"
        self._label.setText(f"Picking for: {self._role_label} — {preview}")

    def _selected_column_names(self) -> list[str]:
        """Display-only preview of the selection (names, not ids).

        Deliberately *not* the id-resolution logic — that lives in
        `DatasetTableView.get_selected_column_ids`, which this class calls for
        the actual result handed back to the wizard.
        """
        if self._table_view is None:
            return []
        dataset = self._table_view.model()._dataset
        if dataset is None or dataset.data is None:
            return []
        columns = list(dataset.data.columns)
        selected = self._table_view.selectionModel().selectedColumns()
        indices = sorted(index.column() for index in selected)
        return [columns[i] for i in indices if i < len(columns)]

    def _selected_column_ids(self) -> list[str]:
        if self._table_view is None:
            return []
        return self._table_view.get_selected_column_ids()

    def _finish(self) -> None:
        column_ids = self._selected_column_ids()
        if self._table_view is not None:
            self._table_view.selectionModel().selectionChanged.disconnect(self._on_selection_changed)
            self._table_view = None
        self.hide()
        if self._wizard is not None:
            # Mirror of start(): hide -> restore modality -> show, so Qt
            # re-registers the wizard as application-modal again.
            self._wizard.hide()
            self._wizard.setWindowModality(self._wizard_previous_modality)
            if self._wizard_previous_geometry is not None:
                self._wizard.setGeometry(self._wizard_previous_geometry)
            self._wizard.show()
            self._wizard.raise_()
        if self._on_done is not None:
            self._on_done(column_ids)
