"""Tests for ProjectPanelCommandManager.create_chart_from_dataset."""
from unittest.mock import Mock, patch

from pandaplot.gui.components.sidebar.project.project_command_manager import ProjectPanelCommandManager


def _fake_selected_item(dataset_obj):
    item = Mock()
    item.data.return_value = {"type": "dataset", "id": dataset_obj.id, "data": dataset_obj}
    return item


@patch("pandaplot.gui.components.sidebar.project.project_command_manager.CreateChartFromWizardCommand")
def test_create_chart_from_dataset_builds_the_wizard_command(mock_command_cls):
    dataset_obj = Mock()
    dataset_obj.id = "ds-1"
    dataset_obj.name = "Sales"
    dataset_obj.parent_id = "folder-1"

    app_context = Mock()
    manager = ProjectPanelCommandManager.__new__(ProjectPanelCommandManager)
    manager.app_context = app_context
    manager.get_current_item = Mock(return_value=_fake_selected_item(dataset_obj))

    manager.create_chart_from_dataset()

    mock_command_cls.assert_called_once_with(
        app_context, dataset_id="ds-1", preselected_column_ids=[], parent_id="folder-1"
    )
    app_context.get_command_executor.return_value.execute_command.assert_called_once_with(
        mock_command_cls.return_value
    )
