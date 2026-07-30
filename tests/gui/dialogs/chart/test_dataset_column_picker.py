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
