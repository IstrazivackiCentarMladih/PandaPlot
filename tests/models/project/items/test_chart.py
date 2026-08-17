"""Tests for the Chart model (pandaplot.models.project.items.chart.Chart)."""

from pandaplot.models.chart.chart_type import ChartType
from pandaplot.models.project.items.chart import Chart


class TestChartTypeIsChartTypeEnum:
    """Chart.chart_type is a ChartType(str, Enum), not a plain str -- but
    every existing string-literal comparison in the codebase keeps
    working, since ChartType subclasses str (same pattern as
    DataSeries.y_axis/YAxis)."""

    def test_constructor_coerces_string_to_charttype(self):
        chart = Chart(name="C", chart_type="scatter")

        assert chart.chart_type == ChartType.SCATTER
        assert isinstance(chart.chart_type, ChartType)

    def test_constructor_accepts_a_charttype_instance_directly(self):
        chart = Chart(name="C", chart_type=ChartType.VECTOR)

        assert chart.chart_type == ChartType.VECTOR

    def test_constructor_defaults_to_line(self):
        chart = Chart(name="C")

        assert chart.chart_type == ChartType.LINE

    def test_set_chart_type_coerces_string(self):
        chart = Chart(name="C", chart_type="line")

        chart.set_chart_type("bar")

        assert chart.chart_type == ChartType.BAR

    def test_string_equality_still_works(self):
        # Existing call sites throughout chart_editor.py/resolve_series_data
        # compare chart.chart_type directly to string literals -- this must
        # keep working unchanged.
        chart = Chart(name="C", chart_type="hist")

        assert chart.chart_type == "hist"
        assert chart.chart_type != "line"

    def test_to_dict_serializes_as_plain_string(self):
        chart = Chart(name="C", chart_type="vector")

        data = chart.to_dict()

        assert data["chart_type"] == "vector"
        assert isinstance(data["chart_type"], str)

    def test_from_dict_round_trips_chart_type(self):
        chart = Chart(name="C", chart_type="scatter")
        data = chart.to_dict()

        restored = Chart.from_dict(data)

        assert restored.chart_type == ChartType.SCATTER

    def test_from_dict_defaults_missing_chart_type_to_line(self):
        restored = Chart.from_dict({"name": "C"})

        assert restored.chart_type == ChartType.LINE
