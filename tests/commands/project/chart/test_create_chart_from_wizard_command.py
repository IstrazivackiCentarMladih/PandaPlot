"""Tests for CreateChartFromWizardCommand."""
from unittest.mock import Mock, patch

import pytest
from PySide6.QtWidgets import QDialog

from pandaplot.commands.project.chart import CreateChartFromWizardCommand


@pytest.fixture
def app_context_with_project():
    dataset = Mock()
    dataset.name = "ds"
    dataset.parent_id = None

    project = Mock()
    project.find_item.return_value = dataset
    project.get_all_items.return_value = [dataset]

    app_state = Mock()
    app_state.has_project = True
    app_state.current_project = project

    app_context = Mock()
    app_context.get_app_state.return_value = app_state
    app_context.get_ui_controller.return_value = Mock()
    app_context.event_bus = Mock()
    return app_context, project


def _fake_wizard(chart_type="line", is_empty=False, series_configs=None):
    wizard = Mock()
    wizard.exec.return_value = QDialog.DialogCode.Accepted
    wizard.get_chart_type.return_value = chart_type
    wizard.is_empty.return_value = is_empty
    wizard.get_series_configs.return_value = series_configs or []
    return wizard


@patch("pandaplot.commands.project.chart.create_chart_from_wizard_command.ChartWizard")
def test_cancelled_wizard_creates_nothing(mock_wizard_cls, app_context_with_project):
    app_context, project = app_context_with_project
    wizard = Mock()
    wizard.exec.return_value = QDialog.DialogCode.Rejected
    mock_wizard_cls.return_value = wizard

    command = CreateChartFromWizardCommand(app_context)

    assert command.execute() is False
    project.add_item.assert_not_called()


@patch("pandaplot.commands.project.chart.create_chart_from_wizard_command.ChartWizard")
def test_empty_path_creates_a_line_chart_with_no_series(mock_wizard_cls, app_context_with_project):
    app_context, project = app_context_with_project
    mock_wizard_cls.return_value = _fake_wizard(chart_type="line", is_empty=True)

    command = CreateChartFromWizardCommand(app_context)

    assert command.execute() is True
    created_chart = project.add_item.call_args[0][0]
    assert created_chart.chart_type == "line"
    assert created_chart.data_series == []


@patch("pandaplot.commands.project.chart.create_chart_from_wizard_command.ChartWizard")
def test_series_configs_become_data_series(mock_wizard_cls, app_context_with_project):
    app_context, project = app_context_with_project
    series_configs = [{
        "dataset_id": "ds-1",
        "x_column_id": "col-date",
        "y_column_id": "col-rev",
        "x_error_column_id": "",
        "y_error_column_id": "",
        "error_symmetric": True,
    }]
    mock_wizard_cls.return_value = _fake_wizard(chart_type="hist", series_configs=series_configs)

    command = CreateChartFromWizardCommand(app_context)

    assert command.execute() is True
    created_chart = project.add_item.call_args[0][0]
    assert created_chart.chart_type == "hist"
    assert len(created_chart.data_series) == 1
    assert created_chart.data_series[0].dataset_id == "ds-1"
    assert created_chart.data_series[0].x_column_id == "col-date"
    assert created_chart.data_series[0].y_column_id == "col-rev"


@patch("pandaplot.commands.project.chart.create_chart_from_wizard_command.ChartWizard")
def test_redo_readds_the_same_chart_instance(mock_wizard_cls, app_context_with_project):
    app_context, project = app_context_with_project
    mock_wizard_cls.return_value = _fake_wizard(chart_type="line", is_empty=True)
    command = CreateChartFromWizardCommand(app_context)

    assert command.execute() is True
    first_id = command.created_chart_id
    first_chart = project.add_item.call_args[0][0]

    command.undo()
    project.remove_item_by_id.assert_called_once_with(first_id)

    command.redo()
    redo_chart = project.add_item.call_args[0][0]
    assert redo_chart is first_chart
    assert command.created_chart_id == first_id
