"""Tests for series_swatch_color, the type-aware "what color represents
this series in a UI swatch" helper. Exists because VectorSeriesStyle has
no `color` field (only `vector_color`) -- data_tab.py's swatch reads
needed a single call that works for all 5 series types without branching
inline at each call site."""
from pandaplot.models.chart.series_swatch_color import series_swatch_color
from pandaplot.models.project.items.chart import DataSeries
from pandaplot.models.chart.series_type import SeriesType


def test_line_series_swatch_color():
    series = DataSeries(dataset_id="ds1", x_column="x", y_column="y",
                         series_type=SeriesType.LINE, color="#112233")

    assert series_swatch_color(series) == "#112233"


def test_bar_series_swatch_color():
    series = DataSeries(dataset_id="ds1", x_column="x", y_column="y",
                         series_type=SeriesType.BAR, color="#445566")

    assert series_swatch_color(series) == "#445566"


def test_vector_series_swatch_color():
    series = DataSeries(dataset_id="ds1", x_column="x", y_column="y",
                         series_type=SeriesType.VECTOR, vector_color="#00ff00")

    assert series_swatch_color(series) == "#00ff00"
