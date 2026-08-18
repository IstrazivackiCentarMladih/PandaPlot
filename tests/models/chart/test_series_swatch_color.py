"""Tests for swatch_color property on SeriesStyleBase and its overrides.
The property provides a type-aware "what color represents this series in a
UI swatch" getter. VectorSeriesStyle overrides it because it has no `color`
field (only `vector_color`)."""
from pandaplot.models.chart.series_style import BarSeriesStyle, LineSeriesStyle, VectorSeriesStyle
from pandaplot.models.chart.series_type import SeriesType
from pandaplot.models.project.items.chart import DataSeries


def test_line_series_swatch_color():
    series = DataSeries(dataset_id="ds1", x_column="x", y_column="y",
                         series_type=SeriesType.LINE, style=LineSeriesStyle(color="#112233"))

    assert series.style.swatch_color == "#112233"


def test_bar_series_swatch_color():
    series = DataSeries(dataset_id="ds1", x_column="x", y_column="y",
                         series_type=SeriesType.BAR, style=BarSeriesStyle(color="#445566"))

    assert series.style.swatch_color == "#445566"


def test_vector_series_swatch_color():
    series = DataSeries(dataset_id="ds1", x_column="x", y_column="y",
                         series_type=SeriesType.VECTOR, style=VectorSeriesStyle(vector_color="#00ff00"))

    assert series.style.swatch_color == "#00ff00"
