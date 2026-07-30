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


def _fake_dataset_tab(selected_columns: list[int]):
    dataset = Mock()
    dataset.data = pd.DataFrame({"Date": [], "Revenue": []})
    dataset.column_id.side_effect = lambda name: {"Date": "col-date", "Revenue": "col-rev"}[name]

    model = Mock()
    model._dataset = dataset

    selection_model = Mock()
    selection_model.selectedColumns.return_value = [Mock(column=Mock(return_value=c)) for c in selected_columns]
    selection_model.selectionChanged = Mock()
    selection_model.selectionChanged.connect = Mock()
    selection_model.selectionChanged.disconnect = Mock()

    table_view = Mock()
    table_view.model.return_value = model
    table_view.selectionModel.return_value = selection_model

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


def test_unresolved_column_id_is_excluded_and_logged(caplog):
    dataset_tab = _fake_dataset_tab(selected_columns=[0, 1])
    dataset = dataset_tab.table_view.model()._dataset
    dataset.column_id.side_effect = lambda name: {"Date": None, "Revenue": "col-rev"}[name]
    app_context, _ = _fake_app_context(dataset_tab)
    picker = DatasetColumnPicker(app_context)
    wizard = QDialog()
    received = []

    with caplog.at_level("WARNING"):
        picker.start(wizard, "ds-1", "Y column", on_done=received.append)
        picker._finish()

    assert received == [["col-rev"]]
    assert any(
        record.levelname == "WARNING" and "Date" in record.getMessage()
        for record in caplog.records
    )
