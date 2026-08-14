"""Tests for ProjectPanelCommandManager.create_chart_from_dataset."""
from unittest.mock import Mock, patch

from pandaplot.gui.components.sidebar.project.project_command_manager import ProjectPanelCommandManager


def _fake_selected_item(dataset_obj):
    item = Mock()
    item.data.return_value = {"type": "dataset", "id": dataset_obj.id, "data": dataset_obj}
    return item


def _manager(app_context, dataset_obj):
    manager = ProjectPanelCommandManager.__new__(ProjectPanelCommandManager)
    manager.logger = Mock()
    manager.app_context = app_context
    manager.get_current_item = Mock(return_value=_fake_selected_item(dataset_obj))
    return manager


def _dataset_obj():
    dataset_obj = Mock()
    dataset_obj.id = "ds-1"
    dataset_obj.name = "Sales"
    dataset_obj.parent_id = "folder-1"
    return dataset_obj


def _app_context_with_tab(dataset_tab):
    """An app context whose TabContainer returns `dataset_tab` for any id."""
    tab_container = Mock()
    tab_container.get_tab_widget.return_value = dataset_tab
    app_context = Mock()
    app_context.get_manager.return_value = tab_container
    return app_context


@patch("pandaplot.gui.components.sidebar.project.project_command_manager.CreateChartFromWizardCommand")
def test_create_chart_from_dataset_preselects_columns_when_the_tab_is_open(mock_command_cls):
    dataset_tab = Mock()
    dataset_tab.table_view.get_selected_column_ids.return_value = ["col-date", "col-rev"]
    app_context = _app_context_with_tab(dataset_tab)
    dataset_obj = _dataset_obj()

    _manager(app_context, dataset_obj).create_chart_from_dataset()

    mock_command_cls.assert_called_once_with(
        app_context,
        dataset_id="ds-1",
        preselected_column_ids=["col-date", "col-rev"],
    )
    app_context.get_command_executor.return_value.execute_command.assert_called_once_with(
        mock_command_cls.return_value
    )


@patch("pandaplot.gui.components.sidebar.project.project_command_manager.CreateChartFromWizardCommand")
def test_create_chart_from_dataset_preselects_nothing_when_the_tab_is_not_open(mock_command_cls):
    # The dataset tab commonly is not open when charting from the project tree.
    app_context = _app_context_with_tab(None)
    dataset_obj = _dataset_obj()

    _manager(app_context, dataset_obj).create_chart_from_dataset()

    mock_command_cls.assert_called_once_with(
        app_context, dataset_id="ds-1", preselected_column_ids=[]
    )
