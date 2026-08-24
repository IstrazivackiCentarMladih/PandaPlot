"""Tests for BaseAnalysisDialog segment index -> (x, y) preview labels."""
import numpy as np
import pandas as pd
import pytest
from PySide6.QtWidgets import QApplication

from pandaplot.gui.dialogs.analysis.base_analysis_dialog import BaseAnalysisDialog
from pandaplot.models.project.items.dataset import Dataset


@pytest.fixture(scope="module", autouse=True)
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


@pytest.fixture
def dataset():
    t = np.linspace(0.0, 10.0, 101)
    return Dataset(id="ds-1", name="Data", data=pd.DataFrame({"t": t, "sq": t ** 2}))


@pytest.fixture
def dialog(dataset):
    return BaseAnalysisDialog(None, dataset)


class TestBaseAnalysisDialogRangeLabels:
    def test_start_label_updates_on_index_change(self, dialog):
        dialog.start_index.setValue(10)

        assert dialog.start_value_label.text() == "x=1, y=1"

    def test_end_index_defaults_to_the_last_point(self, dialog):
        assert dialog.end_index.minimum() == 0
        assert dialog.end_index.value() == 100
        assert dialog.end_value_label.text() == "x=10, y=100"

    def test_end_index_shrinks_the_segment_when_decreased(self, dialog):
        dialog.end_index.setValue(dialog.end_index.value() - 1)

        assert dialog.end_value_label.text() == "x=9.9, y=98.01"

    def test_get_analysis_config_sends_inclusive_end_as_exclusive_boundary(self, dialog):
        dialog.start_index.setValue(0)
        dialog.end_index.setValue(50)
        dialog.result_column_name.setText("result")

        assert dialog.get_analysis_config()["parameters"]["end_index"] == 51

    def test_labels_update_on_column_change(self, dialog):
        dialog.start_index.setValue(20)
        assert dialog.start_value_label.text() == "x=2, y=4"

        dialog.x_column_combo.setCurrentText("sq")
        dialog.y_column_combo.setCurrentText("t")

        assert dialog.start_value_label.text() == "x=4, y=2"

    def test_no_dataset_shows_placeholder(self):
        dialog = BaseAnalysisDialog(None, None)

        assert dialog.start_value_label.text() == "–"
        assert dialog.end_value_label.text() == "–"
