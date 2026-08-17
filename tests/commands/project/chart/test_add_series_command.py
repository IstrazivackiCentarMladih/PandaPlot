"""Tests for AddSeriesCommand."""
from unittest.mock import Mock

import pytest

from pandaplot.commands.project.chart import AddSeriesCommand
from pandaplot.models.project.items.chart import Chart


def _make_app_context_with_chart(chart_type: str):
    chart = Chart(name="Test Chart", chart_type=chart_type)

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
def app_context_with_chart():
    return _make_app_context_with_chart("vector")


@pytest.fixture
def app_context_with_line_chart():
    return _make_app_context_with_chart("line")


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


def test_execute_builds_typed_color_style_for_line_chart(app_context_with_line_chart):
    """A non-vector chart type translates the flat `color` string into the
    style class's `color` field, not `vector_color`."""
    app_context, chart = app_context_with_line_chart

    command = AddSeriesCommand(
        app_context, chart_id=chart.id, dataset_id="ds-1",
        x_column_id="col-x", y_column_id="col-y", color="#112233",
    )
    assert command.execute() is True
    series = chart.data_series[-1]
    assert series.style.color == "#112233"
    assert not hasattr(series.style, "vector_color")


def test_execute_builds_typed_vector_color_style_for_vector_chart(app_context_with_chart):
    """A vector chart type translates the flat `color` string into the
    style class's `vector_color` field, not `color`."""
    app_context, chart = app_context_with_chart

    command = AddSeriesCommand(
        app_context, chart_id=chart.id, dataset_id="ds-1",
        x_column_id="col-x", y_column_id="col-y", color="#112233",
    )
    assert command.execute() is True
    series = chart.data_series[-1]
    assert series.style.vector_color == "#112233"
    assert not hasattr(series.style, "color")


def test_execute_uses_the_explicit_series_type_over_the_chart_type(app_context_with_line_chart):
    """A vector series added to a Line chart (allowed under Line's spec
    only via {LINE, SCATTER} -- but this test exercises passing an
    explicit type regardless of allow-listing, since AddSeriesCommand
    itself doesn't enforce allowed_series_types; that's a UI-layer
    concern for whatever calls this command) gets the passed type, not
    the chart's own."""
    app_context, chart = app_context_with_line_chart
    from pandaplot.models.chart.series_type import SeriesType

    command = AddSeriesCommand(
        app_context, chart_id=chart.id, dataset_id="ds-1",
        x_column_id="col-x", y_column_id="col-y", color="#112233",
        series_type=SeriesType.SCATTER,
    )
    assert command.execute() is True
    series = chart.data_series[-1]
    assert series.series_type == SeriesType.SCATTER
    assert series.style.color == "#112233"


def test_execute_still_derives_from_chart_type_when_series_type_is_not_passed(app_context_with_chart):
    """Existing call sites that don't pass series_type keep today's
    behavior exactly: derive from the chart's own type."""
    app_context, chart = app_context_with_chart  # vector chart

    command = AddSeriesCommand(
        app_context, chart_id=chart.id, dataset_id="ds-1",
        x_column_id="col-x", y_column_id="col-y",
    )
    assert command.execute() is True
    series = chart.data_series[-1]
    from pandaplot.models.chart.series_type import SeriesType
    assert series.series_type == SeriesType.VECTOR
