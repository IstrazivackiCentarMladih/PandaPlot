"""Tests for derive_style, the reflection-based bridge from DataSeries's
flat fields to a typed SeriesStyleBase object.

This exists specifically because DataSeries.style (Phase 3a) cannot be
trusted as always-populated/fresh yet -- nothing populates it for a
series created after Phase 3a shipped, and nothing re-syncs it if the
still-authoritative flat fields are edited afterward (see the Phase 3
section of docs/superpowers/specs/2026-08-16-chart-series-type-architecture-design.md).
derive_style sidesteps that entirely by reading the CURRENT flat fields
fresh every call, using style_cls's own field names as the source of
truth for which fields to pull -- so there is no separately-maintained
field-name list to drift out of sync (unlike migrate_chart_v1_to_v2's
_STYLE_FIELDS_BY_CHART_TYPE, which operates on raw dicts before a
DataSeries exists and can't use this approach)."""
from pandaplot.models.chart.series_style import (
    BarSeriesStyle,
    HistSeriesStyle,
    LineSeriesStyle,
    ScatterSeriesStyle,
    VectorSeriesStyle,
)
from pandaplot.models.chart.series_style_derivation import derive_style
from pandaplot.models.project.items.chart import DataSeries


def test_derives_line_style_from_flat_fields():
    series = DataSeries(
        dataset_id="ds1", x_column="x", y_column="y",
        color="#112233", line_style="dashed", line_width=3.0,
        marker_style="square", marker_size=5.0,
        fill_enabled=True, fill_color="#445566", fill_alpha=0.5,
    )

    style = derive_style(series, LineSeriesStyle)

    assert isinstance(style, LineSeriesStyle)
    assert style.color == "#112233"
    assert style.line_style == "dashed"
    assert style.line_width == 3.0
    assert style.marker_style == "square"
    assert style.marker_size == 5.0
    assert style.fill_enabled is True
    assert style.fill_color == "#445566"
    assert style.fill_alpha == 0.5


def test_derives_scatter_style_ignoring_line_only_fields():
    series = DataSeries(
        dataset_id="ds1", x_column="x", y_column="y",
        color="#112233", marker_style="triangle", marker_size=4.0,
        line_style="dashed",  # present on DataSeries but not on ScatterSeriesStyle
    )

    style = derive_style(series, ScatterSeriesStyle)

    assert isinstance(style, ScatterSeriesStyle)
    assert style.color == "#112233"
    assert style.marker_style == "triangle"
    assert style.marker_size == 4.0
    assert not hasattr(style, "line_style")


def test_derives_bar_style():
    series = DataSeries(dataset_id="ds1", x_column="x", y_column="y", color="#abcdef")

    style = derive_style(series, BarSeriesStyle)

    assert isinstance(style, BarSeriesStyle)
    assert style.color == "#abcdef"


def test_derives_hist_style():
    series = DataSeries(dataset_id="ds1", x_column="", y_column="y", color="#fedcba")

    style = derive_style(series, HistSeriesStyle)

    assert isinstance(style, HistSeriesStyle)
    assert style.color == "#fedcba"


def test_derives_vector_style():
    series = DataSeries(
        dataset_id="ds1", x_column="x", y_column="y",
        vector_color="#00ff00", vector_colormap="plasma", vector_scale=2.0,
        vector_width=0.02, vector_head_width=4.0, vector_head_length=6.0,
        vector_head_axis_length=5.0,
    )

    style = derive_style(series, VectorSeriesStyle)

    assert isinstance(style, VectorSeriesStyle)
    assert style.vector_color == "#00ff00"
    assert style.vector_colormap == "plasma"
    assert style.vector_scale == 2.0
    assert style.vector_width == 0.02
    assert style.vector_head_width == 4.0
    assert style.vector_head_length == 6.0
    assert style.vector_head_axis_length == 5.0


def test_derived_style_is_independent_of_series_style_field():
    """derive_style must read the flat fields, never DataSeries.style --
    even when .style is set (e.g. by migration) to something stale/wrong,
    derive_style must still reflect the current flat fields."""
    series = DataSeries(
        dataset_id="ds1", x_column="x", y_column="y", color="#111111",
        style=LineSeriesStyle(color="#stale-value-should-be-ignored"),
    )

    style = derive_style(series, LineSeriesStyle)

    assert style.color == "#111111"
