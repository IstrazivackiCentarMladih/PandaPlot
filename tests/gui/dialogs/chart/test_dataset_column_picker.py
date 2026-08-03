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


# --- Regression guards for the "picking silently cancels the wizard" bug -----
#
# `QWizard` is a `QDialog`; `QDialog.setVisible(False)` exits the modal event
# loop `dialog.exec()` is blocked in inside CreateChartFromWizardCommand. If the
# picker hides the wizard, `exec()` returns Rejected and the whole wizard result
# is silently discarded. The picker must therefore only resize/reposition it.

def test_start_never_hides_the_visible_wizard():
    dataset_tab = _fake_dataset_tab(selected_columns=[])
    app_context, _ = _fake_app_context(dataset_tab)
    picker = DatasetColumnPicker(app_context)

    wizard = QDialog()
    wizard.show()  # show(), not exec() -- tests cannot block on a modal loop
    assert wizard.isVisible()

    visibility_during_start = []
    original_set_visible = wizard.setVisible

    def _recording_set_visible(visible):
        visibility_during_start.append(visible)
        original_set_visible(visible)

    wizard.setVisible = _recording_set_visible

    picker.start(wizard, "ds-1", "Y column", on_done=lambda ids: None)

    assert False not in visibility_during_start, (
        "picker.start() hid the wizard -- this exits QDialog.exec()'s modal loop "
        "and silently cancels chart creation"
    )
    assert wizard.isVisible()


def test_finish_never_hides_the_wizard_and_restores_its_geometry():
    dataset_tab = _fake_dataset_tab(selected_columns=[1])
    app_context, _ = _fake_app_context(dataset_tab)
    picker = DatasetColumnPicker(app_context)

    wizard = QDialog()
    wizard.setGeometry(30, 40, 640, 480)
    wizard.show()
    original_geometry = wizard.geometry()

    hide_calls = []
    original_set_visible = wizard.setVisible
    wizard.setVisible = lambda visible: (hide_calls.append(visible), original_set_visible(visible))[1]

    picker.start(wizard, "ds-1", "Y column", on_done=lambda ids: None)
    # Shrunk in place, as the design spec asks -- but still visible.
    assert wizard.isVisible()
    assert wizard.size().width() < original_geometry.width()

    picker._finish()

    assert False not in hide_calls
    assert wizard.isVisible()
    assert wizard.geometry() == original_geometry


def test_wizard_exec_would_not_return_early_during_a_pick_session():
    """Integration-style guard: drive a real exec() loop across a pick session.

    `exec()` is entered, the pick session is started and finished from inside
    that loop, and only an explicit `accept()` is allowed to end it. If any
    part of the picker path hid the dialog, `exec()` would return Rejected
    before `accept()` ever ran.

    faulthandler is muted around the nested loop: on Windows, running a modal
    loop under pytest raises a benign COM condition
    (0x8001010d / RPC_E_CANTCALLOUT_ININPUTSYNCCALL) that faulthandler dumps as
    a scary — but harmless and non-failing — traceback.
    """
    import faulthandler

    from PySide6.QtCore import QTimer

    dataset_tab = _fake_dataset_tab(selected_columns=[1])
    app_context, _ = _fake_app_context(dataset_tab)
    picker = DatasetColumnPicker(app_context)

    wizard = QDialog()
    received = []
    accepted = []

    def _run_pick_session():
        picker.start(wizard, "ds-1", "Y column", on_done=received.append)
        QTimer.singleShot(0, _accept)

    def _accept():
        picker._finish()
        accepted.append(True)
        wizard.accept()

    QTimer.singleShot(0, _run_pick_session)
    faulthandler_was_enabled = faulthandler.is_enabled()
    faulthandler.disable()
    try:
        result = wizard.exec()
    finally:
        if faulthandler_was_enabled:
            faulthandler.enable()

    assert accepted == [True], "exec() returned before accept() -- the pick path cancelled the wizard"
    assert result == QDialog.DialogCode.Accepted
    assert received == [["col-rev"]]
