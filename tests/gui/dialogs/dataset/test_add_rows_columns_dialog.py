import pytest
from PySide6.QtWidgets import QApplication, QDialogButtonBox

from pandaplot.gui.dialogs.dataset.add_rows_columns_dialog import (
    AddRowsColumnsDialog,
    DatasetSize,
)


@pytest.fixture(scope="module", autouse=True)
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


def _datasets():
    return [
        DatasetSize(id="ds-1", name="First", rows=10, columns=3),
        DatasetSize(id="ds-2", name="Second", rows=4, columns=7),
    ]


def _ok_button(dialog):
    return dialog.button_box.button(QDialogButtonBox.StandardButton.Ok)


class TestAddRowsColumnsDialog:
    def test_defaults_to_the_first_dataset_and_its_current_size(self):
        dialog = AddRowsColumnsDialog(_datasets())

        assert dialog.get_dataset_id() == "ds-1"
        assert dialog.get_target_rows() == 10
        assert dialog.get_target_columns() == 3
        assert dialog.current_size_label.text() == "10 rows x 3 columns"

    def test_preselects_the_requested_dataset(self):
        dialog = AddRowsColumnsDialog(_datasets(), initial_dataset_id="ds-2")

        assert dialog.get_dataset_id() == "ds-2"
        assert dialog.get_target_rows() == 4
        assert dialog.get_target_columns() == 7

    def test_unknown_initial_dataset_falls_back_to_the_first(self):
        dialog = AddRowsColumnsDialog(_datasets(), initial_dataset_id="missing")

        assert dialog.get_dataset_id() == "ds-1"

    def test_size_cannot_be_reduced_below_the_current_size(self):
        dialog = AddRowsColumnsDialog(_datasets())

        dialog.rows_spinbox.setValue(2)
        dialog.columns_spinbox.setValue(0)

        assert dialog.get_target_rows() == 10
        assert dialog.get_target_columns() == 3

    def test_ok_is_disabled_until_the_size_grows(self):
        dialog = AddRowsColumnsDialog(_datasets())
        assert _ok_button(dialog).isEnabled() is False

        dialog.rows_spinbox.setValue(11)
        assert _ok_button(dialog).isEnabled() is True

        dialog.rows_spinbox.setValue(10)
        assert _ok_button(dialog).isEnabled() is False

        dialog.columns_spinbox.setValue(4)
        assert _ok_button(dialog).isEnabled() is True

    def test_switching_dataset_re_anchors_the_size_widgets(self):
        """Switching from a taller to a shorter dataset must lower the row
        minimum, not keep the previous dataset's size."""
        dialog = AddRowsColumnsDialog(_datasets())
        dialog.rows_spinbox.setValue(20)

        dialog.dataset_combo.setCurrentIndex(1)

        assert dialog.get_dataset_id() == "ds-2"
        assert dialog.get_target_rows() == 4
        assert dialog.get_target_columns() == 7
        assert dialog.current_size_label.text() == "4 rows x 7 columns"
        assert _ok_button(dialog).isEnabled() is False

    def test_empty_dataset_can_be_grown_from_zero(self):
        dialog = AddRowsColumnsDialog([DatasetSize(id="ds-0", name="Empty", rows=0, columns=0)])

        assert dialog.get_target_rows() == 0
        assert _ok_button(dialog).isEnabled() is False

        dialog.rows_spinbox.setValue(5)
        dialog.columns_spinbox.setValue(2)
        assert _ok_button(dialog).isEnabled() is True
