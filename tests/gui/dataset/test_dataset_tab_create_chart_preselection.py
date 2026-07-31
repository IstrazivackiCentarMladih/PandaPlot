"""Tests for DatasetTab.create_chart_from_data passing along selected columns."""
from unittest.mock import Mock

from pandaplot.gui.components.tabs.dataset.dataset_tab import DatasetTab


def test_create_chart_from_data_passes_selected_column_ids():
    dataset = Mock()
    dataset.id = "ds-1"
    dataset.name = "Sales"
    dataset.column_id.side_effect = lambda name: {"Date": "col-date", "Revenue": "col-rev"}[name]

    tab = DatasetTab.__new__(DatasetTab)
    tab.app_context = Mock()
    tab.logger = Mock()
    tab.dataset = dataset

    parent = Mock()
    tab.parent = Mock(return_value=parent)

    table_view = Mock()
    selected_index = Mock()
    selected_index.column.return_value = 1
    table_view.selectionModel.return_value.selectedColumns.return_value = [selected_index]
    table_view.model.return_value._dataset.data.columns = ["Date", "Revenue"]
    tab.table_view = table_view

    tab.create_chart_from_data()

    parent.create_chart_from_dataset.assert_called_once_with(
        "ds-1", "Chart from Sales", preselected_column_ids=["col-rev"]
    )
