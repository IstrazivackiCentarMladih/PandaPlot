"""Tests for CreateChartCommand undo/redo identity."""

from unittest.mock import Mock

import pytest

from pandaplot.commands.project.chart import CreateChartCommand


@pytest.fixture
def app_context_with_project():
    dataset = Mock()
    dataset.name = "ds"
    dataset.data = None  # skip default-series creation

    project = Mock()
    project.find_item.return_value = dataset

    app_state = Mock()
    app_state.has_project = True
    app_state.current_project = project

    app_context = Mock()
    app_context.get_app_state.return_value = app_state
    app_context.get_ui_controller.return_value = Mock()
    app_context.event_bus = Mock()
    return app_context, project


def test_redo_readds_the_same_chart_instance(app_context_with_project):
    app_context, project = app_context_with_project
    command = CreateChartCommand(app_context, dataset_id="ds-1", chart_name="C")

    assert command.execute() is True
    first_id = command.created_chart_id
    first_chart = project.add_item.call_args[0][0]

    command.undo()
    project.remove_item_by_id.assert_called_once_with(first_id)

    command.redo()
    redo_chart = project.add_item.call_args[0][0]
    assert redo_chart is first_chart
    assert command.created_chart_id == first_id
