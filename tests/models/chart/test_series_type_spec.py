"""Tests pinning down SERIES_TYPE_SPECS' values against today's hardcoded
behavior in chart_editor.py/resolve_series_data/style_tab.py, before any of
those call sites are rewired to read from this registry (Task 7).

Source of truth for each value, as it exists today:
- marker_mode: style_tab.py's marker_card is hidden only for vector
  (`marker_card.setVisible(kind == "series" and not is_vector)`); the
  Marker card is shown identically for both line and scatter today,
  including its "markers enabled" on/off toggle. This registry entry
  records the *intended* distinction (line="optional", scatter="required")
  per the original ask (issue #178), but this phase's Task 7 rewrite only
  wires *card-level* visibility (marker_mode != "unsupported") -- it does
  NOT yet hide the "markers enabled" toggle specifically for scatter or
  force markers always-on there. That UI-level distinction between
  "optional" and "required" is left for whichever later phase actually
  reworks the Style tab's marker controls; recording the correct
  marker_mode value now means that phase only has to consume this field,
  not decide what the value should be. bar/hist/vector have no marker
  concept at all ("unsupported").
- supports_line_style: only "line" reads line_style/line_width
  (chart_editor.py:818-824).
- supports_color: pre-Phase-2 style_tab.py's line_card (which houses the
  color/opacity controls that write series.color/series.alpha) was visible
  for `kind == "fit" or (kind == "series" and not is_scatter and not
  is_vector)` -- i.e. true for line/bar/hist, false for scatter/vector.
  chart_editor.py's bar()/hist() branches both read series.color/alpha
  (bar/hist have no line_style concept, but they do use color/alpha).
- supports_fill: only "line" reads fill_* fields (chart_editor.py:834-852).
- supports_error_bars: chart_editor.py:894
  (`if self.chart.chart_type in ("line", "scatter", "bar")`).
- needs_x_column: resolve_series_data's `needs_x_column = chart_type != "hist"`
  (chart_editor.py:362) -- true for everything except hist.
- needs_secondary_columns: resolve_series_data's `if chart_type == "vector"`
  block (chart_editor.py:378) -- true only for vector.
"""
from pandaplot.models.chart.series_style import (
    BarSeriesStyle,
    HistSeriesStyle,
    LineSeriesStyle,
    ScatterSeriesStyle,
    VectorSeriesStyle,
)
from pandaplot.models.chart.series_type import SeriesType
from pandaplot.models.chart.series_type_spec import SERIES_TYPE_SPECS


def test_every_series_type_is_registered():
    """Asserted against the SeriesType enum rather than a hardcoded list --
    a series type with no spec makes every consumer (the renderer dispatch,
    the Style tab's card visibility, DataSeries.__post_init__) KeyError,
    and that stays caught without editing this test per new type."""
    assert set(SERIES_TYPE_SPECS.keys()) == set(SeriesType)


def test_line_spec():
    spec = SERIES_TYPE_SPECS[SeriesType.LINE]
    assert spec.marker_mode == "optional"
    assert spec.supports_line_style is True
    assert spec.supports_color is True
    assert spec.supports_fill is True
    assert spec.supports_error_bars is True
    assert spec.needs_x_column is True
    assert spec.needs_secondary_columns is False


def test_scatter_spec():
    spec = SERIES_TYPE_SPECS[SeriesType.SCATTER]
    assert spec.marker_mode == "required"
    assert spec.supports_line_style is False
    assert spec.supports_color is False
    assert spec.supports_fill is False
    assert spec.supports_error_bars is True
    assert spec.needs_x_column is True
    assert spec.needs_secondary_columns is False


def test_bar_spec():
    spec = SERIES_TYPE_SPECS[SeriesType.BAR]
    assert spec.marker_mode == "unsupported"
    assert spec.supports_line_style is False
    assert spec.supports_color is True
    assert spec.supports_fill is False
    assert spec.supports_error_bars is True
    assert spec.needs_x_column is True
    assert spec.needs_secondary_columns is False


def test_hist_spec():
    spec = SERIES_TYPE_SPECS[SeriesType.HIST]
    assert spec.marker_mode == "unsupported"
    assert spec.supports_line_style is False
    assert spec.supports_color is True
    assert spec.supports_fill is False
    assert spec.supports_error_bars is False
    assert spec.needs_x_column is False
    assert spec.needs_secondary_columns is False


def test_vector_spec():
    spec = SERIES_TYPE_SPECS[SeriesType.VECTOR]
    assert spec.marker_mode == "unsupported"
    assert spec.supports_line_style is False
    assert spec.supports_color is False
    assert spec.supports_fill is False
    assert spec.supports_error_bars is False
    assert spec.needs_x_column is True
    assert spec.needs_secondary_columns is True


def test_style_cls_matches_each_series_type():
    assert SERIES_TYPE_SPECS[SeriesType.LINE].style_cls is LineSeriesStyle
    assert SERIES_TYPE_SPECS[SeriesType.SCATTER].style_cls is ScatterSeriesStyle
    assert SERIES_TYPE_SPECS[SeriesType.BAR].style_cls is BarSeriesStyle
    assert SERIES_TYPE_SPECS[SeriesType.HIST].style_cls is HistSeriesStyle
    assert SERIES_TYPE_SPECS[SeriesType.VECTOR].style_cls is VectorSeriesStyle
