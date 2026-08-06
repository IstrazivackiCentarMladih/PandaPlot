"""Tests for TabContainer.create_chart_from_dataset routing through the wizard."""
from unittest.mock import Mock, patch

from pandaplot.gui.components.tabs.tab_container import TabContainer


@patch("pandaplot.gui.components.tabs.tab_container.CreateChartFromWizardCommand")
def test_create_chart_from_dataset_builds_the_wizard_command(mock_command_cls):
    dataset_item = Mock()
    dataset_item.parent_id = "folder-1"

    project = Mock()
    project.find_item.return_value = dataset_item

    app_state = Mock()
    app_state.has_project = True
    app_state.current_project = project

    app_context = Mock()
    app_context.get_app_state.return_value = app_state

    container = TabContainer.__new__(TabContainer)
    container.app_context = app_context
    container.logger = Mock()
    # open_tab isn't under test here and requires state __new__ doesn't set up
    # (e.g. self.tabs); stub it so the wizard-command assertion below isn't
    # obscured by an unrelated AttributeError.
    container.open_tab = Mock()

    container.create_chart_from_dataset("ds-1", preselected_column_ids=["col-rev"])

    mock_command_cls.assert_called_once_with(
        app_context, dataset_id="ds-1", preselected_column_ids=["col-rev"]
    )
