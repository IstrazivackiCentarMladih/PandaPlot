"""Tests for the 5 typed per-series-type style dataclasses.

Field lists and defaults are pinned against DataSeries's current flat
fields (pandaplot/models/project/items/chart.py) and chart_editor.py's
per-type rendering branches (lines 818-892) -- each style class holds
exactly the fields that type's branch reads today, no more, no less.
Column-reference fields (u_column_id, v_column_id, ...) and error-bar
fields stay on DataSeries directly in this sub-phase; only the
line/marker/fill/vector-appearance fields move here.
"""
import dataclasses

from pandaplot.models.chart.series_style import (
    BarSeriesStyle,
    HistSeriesStyle,
    LineSeriesStyle,
    ScatterSeriesStyle,
    SeriesStyleBase,
    VectorSeriesStyle,
)


def test_all_style_classes_subclass_series_style_base():
    for cls in (LineSeriesStyle, ScatterSeriesStyle, BarSeriesStyle, HistSeriesStyle, VectorSeriesStyle):
        assert issubclass(cls, SeriesStyleBase)


def test_line_series_style_fields_and_defaults():
    style = LineSeriesStyle()
    assert style.color == "#1f77b4"
    assert style.marker_color == ""
    assert style.marker_edge_color == "#000000"
    assert style.marker_edge_width == 1.0
    assert style.line_style == "solid"
    assert style.marker_style == "circle"
    assert style.line_width == 2.0
    assert style.marker_size == 2.0
    assert style.fill_enabled is False
    assert style.fill_color == ""
    assert style.fill_alpha == 0.3
    assert style.fill_orientation == "vertical"
    assert style.fill_base == 0.0
    assert style.fill_to_index == -1
    assert {f.name for f in dataclasses.fields(style)} == {
        "color", "marker_color", "marker_edge_color", "marker_edge_width",
        "line_style", "marker_style", "line_width", "marker_size",
        "fill_enabled", "fill_color", "fill_alpha", "fill_orientation",
        "fill_base", "fill_to_index",
    }


def test_scatter_series_style_fields_and_defaults():
    style = ScatterSeriesStyle()
    assert style.color == "#1f77b4"
    assert style.marker_color == ""
    assert style.marker_edge_color == "#000000"
    assert style.marker_edge_width == 1.0
    assert style.marker_style == "circle"
    assert style.marker_size == 2.0
    assert {f.name for f in dataclasses.fields(style)} == {
        "color", "marker_color", "marker_edge_color", "marker_edge_width",
        "marker_style", "marker_size",
    }


def test_bar_series_style_fields_and_defaults():
    style = BarSeriesStyle()
    assert style.color == "#1f77b4"
    assert {f.name for f in dataclasses.fields(style)} == {"color"}


def test_hist_series_style_fields_and_defaults():
    style = HistSeriesStyle()
    assert style.color == "#1f77b4"
    assert {f.name for f in dataclasses.fields(style)} == {"color"}


def test_vector_series_style_fields_and_defaults():
    style = VectorSeriesStyle()
    assert style.vector_color == "#1f77b4"
    assert style.vector_colormap == ""
    assert style.vector_scale == 0.0
    assert style.vector_width == 0.005
    assert style.vector_head_width == 3.0
    assert style.vector_head_length == 5.0
    assert style.vector_head_axis_length == 4.5
    assert {f.name for f in dataclasses.fields(style)} == {
        "vector_color", "vector_colormap", "vector_scale", "vector_width",
        "vector_head_width", "vector_head_length", "vector_head_axis_length",
    }
