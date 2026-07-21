"""
Unit tests for ErrorDirection, the StrEnum backing DataSeries.error_direction.

Covers:
- ErrorDirection compares equal to its plain string value (StrEnum contract)
- DataSeries defaults to ErrorDirection.BOTH
- Chart serialization round-trips error_direction as an ErrorDirection member,
  including loading an older/hand-written plain-string save file
"""

from pandaplot.models.project.items.chart import Chart, DataSeries, ErrorDirection


def test_error_direction_is_a_str_enum():
    assert ErrorDirection.BOTH == "both"
    assert ErrorDirection.PLUS == "plus"
    assert ErrorDirection.MINUS == "minus"
    assert isinstance(ErrorDirection.BOTH, str)


def test_data_series_defaults_to_both():
    series = DataSeries(dataset_id="ds1", x_column="x", y_column="y")
    assert series.error_direction is ErrorDirection.BOTH


def test_chart_serialization_round_trips_error_direction():
    chart = Chart(name="Test Chart", chart_type="line")
    chart.add_data_series(
        dataset_id="ds1", x_column="x", y_column="y", error_direction=ErrorDirection.PLUS
    )

    data = chart.to_dict()
    assert data["data_series"][0]["error_direction"] == "plus"

    restored = Chart.from_dict(data)
    assert restored.data_series[0].error_direction is ErrorDirection.PLUS


def test_chart_deserialization_coerces_plain_string_to_enum():
    """Older saves (or hand-edited project files) store a plain string;
    from_dict must still hand back a real ErrorDirection member."""
    chart = Chart(name="Test Chart", chart_type="line")
    data = chart.to_dict()
    data["data_series"] = [{
        "dataset_id": "ds1", "x_column": "x", "y_column": "y",
        "error_direction": "minus",
    }]

    restored = Chart.from_dict(data)
    assert restored.data_series[0].error_direction is ErrorDirection.MINUS
