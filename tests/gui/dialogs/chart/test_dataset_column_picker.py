"""Tests for DatasetColumnPicker."""
from unittest.mock import Mock

import pandas as pd
import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QDialog

from pandaplot.gui.dialogs.chart.dataset_column_picker import DatasetColumnPicker


@pytest.fixture(scope="module", autouse=True)
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


@pytest.fixture(autouse=True)
def no_leaked_modal_windows(qapp):
    """Hide every top-level widget after each test.

    Several tests leave a visible application-modal `QDialog` behind, which
    stays registered in `QApplication.modalWindow()` and would otherwise make
    the modal-registration assertions below see a stale blocker.
    """
    yield
    for widget in QApplication.topLevelWidgets():
        widget.hide()


_COLUMN_IDS = {"Date": "col-date", "Revenue": "col-rev"}


def _fake_dataset_tab(selected_columns: list[int]):
    """A dataset tab whose table view behaves like `DatasetTableView` does.

    In particular `get_selected_column_ids()` is the real contract the picker
    now depends on (id resolution lives in `DatasetTableView`), so the fake
    provides it alongside the model/selection-model used for the name preview.
    """
    dataset = Mock()
    dataset.data = pd.DataFrame({"Date": [], "Revenue": []})
    dataset.column_id.side_effect = lambda name: _COLUMN_IDS[name]

    model = Mock()
    model._dataset = dataset

    selection_model = Mock()
    selection_model.selectedColumns.return_value = [Mock(column=Mock(return_value=c)) for c in selected_columns]
    selection_model.selectionChanged = Mock()
    selection_model.selectionChanged.connect = Mock()
    selection_model.selectionChanged.disconnect = Mock()

    columns = list(dataset.data.columns)
    table_view = Mock()
    table_view.model.return_value = model
    table_view.selectionModel.return_value = selection_model
    table_view.get_selected_column_ids.side_effect = lambda: [
        column_id
        for column_id in (dataset.column_id(columns[i]) for i in sorted(selected_columns) if i < len(columns))
        if column_id
    ]

    dataset_tab = Mock()
    dataset_tab.table_view = table_view
    return dataset_tab


def _fake_app_context(dataset_tab):
    tab_container = Mock()
    tab_container.get_tab_widget.return_value = dataset_tab

    app_context = Mock()
    app_context.get_manager.return_value = tab_container
    return app_context, tab_container


def test_start_opens_and_focuses_the_dataset_tab():
    dataset_tab = _fake_dataset_tab(selected_columns=[])
    app_context, tab_container = _fake_app_context(dataset_tab)
    picker = DatasetColumnPicker(app_context)
    wizard = QDialog()

    picker.start(wizard, "ds-1", "Y column", on_done=lambda ids: None)

    tab_container.open_tab.assert_called_once_with("ds-1")


def test_start_makes_the_wizard_non_modal():
    dataset_tab = _fake_dataset_tab(selected_columns=[])
    app_context, _ = _fake_app_context(dataset_tab)
    picker = DatasetColumnPicker(app_context)
    wizard = QDialog()
    wizard.setWindowModality(Qt.WindowModality.ApplicationModal)

    picker.start(wizard, "ds-1", "Y column", on_done=lambda ids: None)

    assert wizard.windowModality() == Qt.WindowModality.NonModal


def test_done_restores_modal_state_and_reports_selected_column_ids():
    dataset_tab = _fake_dataset_tab(selected_columns=[1])
    app_context, _ = _fake_app_context(dataset_tab)
    picker = DatasetColumnPicker(app_context)
    wizard = QDialog()
    wizard.setWindowModality(Qt.WindowModality.ApplicationModal)
    received = []

    picker.start(wizard, "ds-1", "Y column", on_done=received.append)
    picker._finish()

    assert received == [["col-rev"]]
    assert wizard.windowModality() == Qt.WindowModality.ApplicationModal


def test_done_with_no_selection_reports_empty_list():
    dataset_tab = _fake_dataset_tab(selected_columns=[])
    app_context, _ = _fake_app_context(dataset_tab)
    picker = DatasetColumnPicker(app_context)
    wizard = QDialog()
    received = []

    picker.start(wizard, "ds-1", "Y column", on_done=received.append)
    picker._finish()

    assert received == [[]]


def test_start_called_again_disconnects_previous_session_before_reconnecting():
    first_tab = _fake_dataset_tab(selected_columns=[])
    second_tab = _fake_dataset_tab(selected_columns=[])
    app_context = Mock()
    tab_container = Mock()
    tab_container.get_tab_widget.side_effect = [first_tab, second_tab]
    app_context.get_manager.return_value = tab_container
    picker = DatasetColumnPicker(app_context)
    wizard1 = QDialog()
    wizard2 = QDialog()

    picker.start(wizard1, "ds-1", "Y column", on_done=lambda ids: None)
    first_selection_model = first_tab.table_view.selectionModel()
    first_selection_model.selectionChanged.disconnect.assert_not_called()

    picker.start(wizard2, "ds-2", "X column", on_done=lambda ids: None)

    first_selection_model.selectionChanged.disconnect.assert_called_once_with(
        picker._on_selection_changed
    )
    second_selection_model = second_tab.table_view.selectionModel()
    second_selection_model.selectionChanged.connect.assert_called_once_with(
        picker._on_selection_changed
    )
    second_selection_model.selectionChanged.disconnect.assert_not_called()


def test_finish_drops_the_table_view_so_a_later_finish_cannot_double_disconnect():
    dataset_tab = _fake_dataset_tab(selected_columns=[1])
    app_context, _ = _fake_app_context(dataset_tab)
    picker = DatasetColumnPicker(app_context)
    wizard = QDialog()
    selection_model = dataset_tab.table_view.selectionModel()

    picker.start(wizard, "ds-1", "Y column", on_done=lambda ids: None)
    picker._finish()
    picker._finish()

    assert picker._table_view is None
    selection_model.selectionChanged.disconnect.assert_called_once_with(
        picker._on_selection_changed
    )


def test_unresolved_column_id_is_excluded():
    dataset_tab = _fake_dataset_tab(selected_columns=[0, 1])
    dataset = dataset_tab.table_view.model()._dataset
    dataset.column_id.side_effect = lambda name: {"Date": None, "Revenue": "col-rev"}[name]
    app_context, _ = _fake_app_context(dataset_tab)
    picker = DatasetColumnPicker(app_context)
    wizard = QDialog()
    received = []

    picker.start(wizard, "ds-1", "Y column", on_done=received.append)
    picker._finish()

    assert received == [["col-rev"]]


# --- Regression guards for "the main window never actually unblocks" --------
#
# Qt only updates a window's modal-blocking registration on show()/hide();
# `setWindowModality()` on an already-visible window is a documented no-op
# until the next hide/show cycle. So the picker MUST hide -> change modality ->
# show the wizard, otherwise the main window stays input-blocked and dataset
# column-header clicks are swallowed. This is safe because
# `CreateChartFromWizardCommand` opens the wizard with `show()` and reacts to
# its `finished` signal -- there is no blocking `exec()` loop to tear down.

def _record_visibility(widget) -> list[bool]:
    """Record every setVisible() call on `widget`, still applying it for real."""
    calls: list[bool] = []
    original_set_visible = widget.setVisible

    def _recording_set_visible(visible):
        calls.append(visible)
        original_set_visible(visible)

    widget.setVisible = _recording_set_visible
    return calls


def test_start_performs_a_real_hide_then_show_cycle_on_the_wizard():
    dataset_tab = _fake_dataset_tab(selected_columns=[])
    app_context, _ = _fake_app_context(dataset_tab)
    picker = DatasetColumnPicker(app_context)

    wizard = QDialog()
    wizard.setWindowModality(Qt.WindowModality.ApplicationModal)
    wizard.show()
    assert wizard.isVisible()

    visibility_calls = _record_visibility(wizard)

    picker.start(wizard, "ds-1", "Y column", on_done=lambda ids: None)

    assert visibility_calls == [False, True], (
        "start() must hide then re-show the wizard -- Qt ignores a modality "
        "change made while the window is visible, leaving the main window "
        "blocked so dataset column clicks do nothing"
    )
    assert wizard.windowModality() == Qt.WindowModality.NonModal
    assert wizard.isVisible()


def test_start_changes_modality_between_the_hide_and_the_show():
    """Ordering matters: the modality change must land while hidden."""
    dataset_tab = _fake_dataset_tab(selected_columns=[])
    app_context, _ = _fake_app_context(dataset_tab)
    picker = DatasetColumnPicker(app_context)

    wizard = QDialog()
    wizard.setWindowModality(Qt.WindowModality.ApplicationModal)
    wizard.show()

    events: list[str] = []
    original_set_visible = wizard.setVisible
    original_set_modality = wizard.setWindowModality

    def _recording_set_visible(visible):
        events.append("show" if visible else "hide")
        original_set_visible(visible)

    def _recording_set_modality(modality):
        events.append(f"modality:{modality.name}")
        original_set_modality(modality)

    wizard.setVisible = _recording_set_visible
    wizard.setWindowModality = _recording_set_modality

    picker.start(wizard, "ds-1", "Y column", on_done=lambda ids: None)

    assert events == ["hide", "modality:NonModal", "show"]


def test_finish_restores_modality_with_a_hide_show_cycle_and_the_geometry():
    dataset_tab = _fake_dataset_tab(selected_columns=[1])
    app_context, _ = _fake_app_context(dataset_tab)
    picker = DatasetColumnPicker(app_context)

    wizard = QDialog()
    wizard.setWindowModality(Qt.WindowModality.ApplicationModal)
    wizard.setGeometry(30, 40, 640, 480)
    wizard.show()
    original_geometry = wizard.geometry()

    picker.start(wizard, "ds-1", "Y column", on_done=lambda ids: None)
    # Shrunk to a small floating bar for the pick session, and still visible.
    assert wizard.isVisible()
    assert wizard.size().width() < original_geometry.width()

    visibility_calls = _record_visibility(wizard)

    picker._finish()

    assert visibility_calls == [False, True], (
        "_finish() must hide then re-show the wizard so Qt re-registers it as "
        "application-modal; otherwise it stays blocking-but-nonmodal forever"
    )
    assert wizard.windowModality() == Qt.WindowModality.ApplicationModal
    assert wizard.isVisible()
    assert wizard.geometry() == original_geometry


def test_the_main_window_is_really_unblocked_and_reblocked_by_a_pick_session():
    """The strongest form of the guard: ask Qt itself, not just the property.

    `QApplication.modalWindow()` is Qt's own view of what is blocking input.
    Pre-fix it stayed pointed at the wizard for the whole pick session (because
    `setWindowModality()` on a visible window is a no-op), which is exactly why
    clicking dataset column headers did nothing.
    """
    dataset_tab = _fake_dataset_tab(selected_columns=[1])
    app_context, _ = _fake_app_context(dataset_tab)
    picker = DatasetColumnPicker(app_context)

    wizard = QDialog()
    wizard.setModal(True)
    wizard.show()
    assert QApplication.modalWindow() is wizard.windowHandle()

    picker.start(wizard, "ds-1", "Y column", on_done=lambda ids: None)
    assert QApplication.modalWindow() is None, (
        "the main window is still input-blocked during the pick session"
    )

    picker._finish()
    assert QApplication.modalWindow() is wizard.windowHandle(), (
        "the wizard was not re-registered as the modal window after picking"
    )

    wizard.hide()  # don't leak a modal window into sibling tests


def test_a_full_pick_session_leaves_the_wizard_visible_and_modal_again():
    """End-to-end invariant: no residual blocking-but-nonmodal state.

    The pre-fix failure mode was a wizard left registered as blocking while
    non-modal, freezing all application input until restart. After a complete
    start -> finish round trip the wizard must be back exactly as it was.
    """
    dataset_tab = _fake_dataset_tab(selected_columns=[1])
    app_context, _ = _fake_app_context(dataset_tab)
    picker = DatasetColumnPicker(app_context)

    wizard = QDialog()
    wizard.setWindowModality(Qt.WindowModality.ApplicationModal)
    wizard.setGeometry(30, 40, 640, 480)
    wizard.show()
    received = []

    picker.start(wizard, "ds-1", "Y column", on_done=received.append)
    assert wizard.windowModality() == Qt.WindowModality.NonModal

    picker._finish()

    assert received == [["col-rev"]]
    assert wizard.windowModality() == Qt.WindowModality.ApplicationModal
    assert wizard.isVisible()
    assert not picker.isVisible()
