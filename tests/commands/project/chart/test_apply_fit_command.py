"""Tests for ApplyFitCommand execute, undo, and redo."""

from unittest.mock import Mock

import pytest

from pandaplot.commands.project.chart.apply_fit_command import ApplyFitCommand
from pandaplot.models.project.items.chart import Chart


@pytest.fixture
def app_context_with_chart():
    chart = Chart(name="Chart")

    project = Mock()
    project.find_item.return_value = chart

    app_state = Mock()
    app_state.has_project = True
    app_state.current_project = project

    app_context = Mock()
    app_context.get_app_state.return_value = app_state
    app_context.event_bus = Mock()

    return app_context, chart


@pytest.fixture
def fit_results():
    return Mock(
        fit_type="linear",
        x_fit=[1, 2, 3],
        y_fit=[2, 4, 6],
        param_names=["slope", "intercept"],
        params=[2.0, 0.0],
        r_squared=0.99,
        confidence_lower=None,
        confidence_upper=None,
    )


def test_execute_adds_fit_to_chart(app_context_with_chart, fit_results):
    app_context, chart = app_context_with_chart

    command = ApplyFitCommand(
        app_context=app_context,
        chart_id=chart.id,
        fit_results=fit_results,
        source_dataset_id="ds1",
        source_x_column_id="x_id",
        source_y_column_id="y_id",
        source_x_column="x",
        source_y_column="y",
        label="Linear fit",
    )

    assert command.execute() is True

    assert len(chart.fit_data) == 1
    assert command.added_index == 0

    fit = chart.fit_data[0]

    assert fit.fit_type == "linear"
    assert fit.x_data == [1, 2, 3]
    assert fit.y_data == [2, 4, 6]
    assert fit.source_dataset_id == "ds1"
    assert fit.source_x_column_id == "x_id"
    assert fit.source_y_column_id == "y_id"
    assert fit.source_x_column == "x"
    assert fit.source_y_column == "y"
    assert fit.label == "Linear fit"


def test_undo_removes_fit_from_chart(app_context_with_chart, fit_results):
    app_context, chart = app_context_with_chart

    command = ApplyFitCommand(
        app_context=app_context,
        chart_id=chart.id,
        fit_results=fit_results,
        source_dataset_id="ds1",
        source_x_column_id="x_id",
        source_y_column_id="y_id",
    )

    assert command.execute() is True
    assert len(chart.fit_data) == 1

    command.undo()

    assert len(chart.fit_data) == 0


def test_redo_adds_fit_again(app_context_with_chart, fit_results):
    app_context, chart = app_context_with_chart

    command = ApplyFitCommand(
        app_context=app_context,
        chart_id=chart.id,
        fit_results=fit_results,
        source_dataset_id="ds1",
        source_x_column_id="x_id",
        source_y_column_id="y_id",
    )

    command.execute()
    command.undo()

    assert len(chart.fit_data) == 0

    command.redo()

    assert len(chart.fit_data) == 1

    fit = chart.fit_data[0]
    assert fit.fit_type == "linear"
    assert fit.x_data == [1, 2, 3]
    assert fit.y_data == [2, 4, 6]
