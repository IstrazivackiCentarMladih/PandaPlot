import math

import pytest
from PySide6.QtWidgets import QApplication

from pandaplot.gui.dialogs.dataset.new_dataset_dialog import NewDatasetDialog


@pytest.fixture(scope="module", autouse=True)
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


class TestNewDatasetDialog:
    def test_defaults(self):
        dialog = NewDatasetDialog()

        assert dialog.get_dataset_name() == "New Dataset"
        assert dialog.get_rows() == 10
        assert dialog.get_columns() == 3
        assert math.isnan(dialog.get_fill_value())

    def test_fill_value_zero_when_second_combo_option_selected(self):
        dialog = NewDatasetDialog()
        dialog.fill_value_combo.setCurrentIndex(1)

        assert dialog.get_fill_value() == 0.0

    def test_rows_and_columns_reflect_spinbox_values(self):
        dialog = NewDatasetDialog()
        dialog.rows_spinbox.setValue(25)
        dialog.columns_spinbox.setValue(7)

        assert dialog.get_rows() == 25
        assert dialog.get_columns() == 7

    def test_ok_button_disabled_when_name_is_empty(self):
        dialog = NewDatasetDialog()
        ok_button = dialog.button_box.button(dialog.button_box.StandardButton.Ok)

        dialog.name_edit.setText("")
        assert ok_button.isEnabled() is False

        dialog.name_edit.setText("   ")
        assert ok_button.isEnabled() is False

        dialog.name_edit.setText("My Dataset")
        assert ok_button.isEnabled() is True

    def test_rows_and_columns_spinbox_minimum_is_one(self):
        dialog = NewDatasetDialog()

        dialog.rows_spinbox.setValue(0)
        assert dialog.rows_spinbox.value() == 1

        dialog.columns_spinbox.setValue(-5)
        assert dialog.columns_spinbox.value() == 1
