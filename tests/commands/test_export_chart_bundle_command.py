"""Tests for ExportChartBundleCommand."""

import os
from unittest.mock import MagicMock

import pandas as pd
import pytest

from pandaplot.commands.base_command import CommandResult
from pandaplot.commands.project.chart.export_chart_bundle_command import ExportChartBundleCommand
from pandaplot.models.chart.chart_type import ChartType
from pandaplot.models.project.items.chart import Chart
from pandaplot.models.project.items.dataset import Dataset
from pandaplot.models.project.project import Project


@pytest.fixture
def mock_app_context():
    app_context = MagicMock()
    app_state = MagicMock()
    ui_controller = MagicMock()
    task_scheduler = MagicMock()

    app_context.get_app_state.return_value = app_state
    app_context.get_ui_controller.return_value = ui_controller
    app_context.get_task_scheduler.return_value = task_scheduler

    # Setup task_scheduler.run_task to immediately execute the task function
    def immediate_run_task(task, task_arguments, on_result=None, on_error=None, on_finished=None, on_progress=None):
        try:
            res = task(progress_callback=on_progress, **task_arguments)
            if on_result:
                on_result(res)
            if on_finished:
                on_finished()
        except Exception as e:
            if on_error:
                on_error((type(e), e, None))
            if on_finished:
                on_finished()

    task_scheduler.run_task.side_call = immediate_run_task
    task_scheduler.run_task.side_effect = immediate_run_task

    return app_context, app_state, ui_controller, task_scheduler


@pytest.fixture
def sample_project():
    project = Project(name="Command Test Project")
    ds = Dataset(name="Dataset 1")
    ds.set_data(pd.DataFrame({"x": [1, 2], "y": [3, 4]}))
    project.add_item(ds)

    chart = Chart(name="Command Test Chart", chart_type=ChartType.LINE)
    s = chart.add_data_series(dataset_id=ds.id, x_column="x", y_column="y")
    s.x_column_id = ds.column_id("x")
    s.y_column_id = ds.column_id("y")
    project.add_item(chart)

    return project, chart, ds


def test_command_properties(mock_app_context):
    app_context, _, _, _ = mock_app_context
    cmd = ExportChartBundleCommand(app_context, chart_id="dummy_id")

    assert cmd.marks_project_modified() is False
    assert cmd.occupies_undo_slot() is False
    assert cmd.undo() == CommandResult.NOOP


def test_command_fails_when_no_project(mock_app_context):
    app_context, app_state, ui_controller, _ = mock_app_context
    app_state.has_project = False

    cmd = ExportChartBundleCommand(app_context, chart_id="dummy_id")
    result = cmd.execute()

    assert result == CommandResult.FAILURE
    ui_controller.show_warning_message.assert_called_once()


def test_command_fails_when_chart_not_found(mock_app_context, sample_project):
    project, chart, ds = sample_project
    app_context, app_state, ui_controller, _ = mock_app_context

    app_state.has_project = True
    app_state.current_project = project

    cmd = ExportChartBundleCommand(app_context, chart_id="non_existent_id")
    result = cmd.execute()

    assert result == CommandResult.FAILURE
    ui_controller.show_error_message.assert_called_once()


def test_command_user_cancels_dialog(mock_app_context, sample_project):
    project, chart, ds = sample_project
    app_context, app_state, ui_controller, _ = mock_app_context

    app_state.has_project = True
    app_state.current_project = project
    ui_controller.show_export_chart_bundle_dialog.return_value = None  # User clicked cancel

    cmd = ExportChartBundleCommand(app_context, chart_id=chart.id)
    result = cmd.execute()

    assert result == CommandResult.FAILURE
    ui_controller.show_export_chart_bundle_dialog.assert_called_once_with(chart.name)


def test_command_export_success(tmp_path, mock_app_context, sample_project):
    project, chart, ds = sample_project
    app_context, app_state, ui_controller, _ = mock_app_context

    app_state.has_project = True
    app_state.current_project = project

    export_path = str(tmp_path / "bundle.zip")
    ui_controller.show_export_chart_bundle_dialog.return_value = export_path

    cmd = ExportChartBundleCommand(app_context, chart_id=chart.id)
    result = cmd.execute()

    assert result == CommandResult.SUCCESS
    assert os.path.exists(export_path)
    ui_controller.show_info_message.assert_called()
