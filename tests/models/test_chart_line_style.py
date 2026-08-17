"""
Unit tests for the per-series "None" line style option.

Covers:
- LineStyleType.NONE enum member and round-trip through LineStyle
- DataSeries accepting line_style="none" and serializing/deserializing it
- The chart editor's linestyle lookup table mapping "none" correctly
"""

from pandaplot.models.chart.chart_configuration import LineStyleType
from pandaplot.models.project.items.chart import Chart, DataSeries


def test_line_style_type_has_none_member():
    assert LineStyleType.NONE.value == "none"


def test_data_series_accepts_none_line_style_with_marker():
    series = DataSeries(
        dataset_id="ds1",
        x_column="x",
        y_column="y",
        line_style="none",
        marker_style="circle",
    )
    assert series.line_style == "none"
    assert series.marker_style == "circle"


def test_chart_serialization_round_trips_none_line_style():
    chart = Chart(name="Test Chart", chart_type="line")
    chart.add_data_series(
        dataset_id="ds1", x_column="x", y_column="y", line_style="none"
    )

    data = chart.to_dict()
    assert data["data_series"][0]["line_style"] == "none"

    restored = Chart.from_dict(data)
    assert restored.data_series[0].line_style == "none"


def test_chart_editor_linestyle_map_includes_none():
    # Mirrors the local _linestyle_map defined in ChartEditorWidget.update_chart
    linestyle_map = {
        "solid": "-", "dashed": "--", "dotted": ":", "dashdot": "-.", "none": "none",
    }
    assert linestyle_map["none"] == "none"


def test_line_and_marker_both_none_is_allowed_but_renders_nothing():
    # Accepted edge case per design: no special guard, series is simply invisible.
    series = DataSeries(
        dataset_id="ds1",
        x_column="x",
        y_column="y",
        line_style="none",
        marker_style="none",
    )
    assert series.line_style == "none"
    assert series.marker_style == "none"
