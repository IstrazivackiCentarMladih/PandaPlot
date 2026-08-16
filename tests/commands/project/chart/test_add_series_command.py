"""Tests for AddSeriesCommand."""
from unittest.mock import Mock

import pytest

from pandaplot.commands.project.chart import AddSeriesCommand
from pandaplot.models.project.items.chart import Chart


@pytest.fixture
def app_context_with_chart():
    chart = Chart(name="Test Chart", chart_type="vector")

    project = Mock()
    project.find_item.return_value = chart

    app_state = Mock()
    app_state.has_project = True
    app_state.current_project = project

    app_context = Mock()
    app_context.get_app_state.return_value = app_state
    app_context.event_bus = Mock()
    return app_context, chart


def test_execute_passes_through_u_v_magnitude_column_ids(app_context_with_chart):
    app_context, chart = app_context_with_chart

    command = AddSeriesCommand(
        app_context, chart_id=chart.id, dataset_id="ds-1",
        x_column_id="col-x", y_column_id="col-y",
        u_column_id="col-u", v_column_id="col-v", magnitude_column_id="col-m",
    )
    assert command.execute() is True
    series = chart.data_series[-1]
    assert series.u_column_id == "col-u"
    assert series.v_column_id == "col-v"
    assert series.magnitude_column_id == "col-m"


def test_execute_defaults_u_v_magnitude_to_empty_string(app_context_with_chart):
    """Existing call sites that don't pass the new params keep working
    unchanged: the series' vector fields default to empty."""
    app_context, chart = app_context_with_chart

    command = AddSeriesCommand(
        app_context, chart_id=chart.id, dataset_id="ds-1",
        x_column_id="col-x", y_column_id="col-y",
    )
    assert command.execute() is True
    series = chart.data_series[-1]
    assert series.u_column_id == ""
    assert series.v_column_id == ""
    assert series.magnitude_column_id == ""
