from pandaplot.models.chart.chart_type import ChartType
from pandaplot.models.chart.chart_type_spec import CHART_TYPE_SPECS
from pandaplot.models.chart.series_type import SeriesType
from pandaplot.models.chart.series_type_spec import SERIES_TYPE_SPECS


def test_colormap_series_spec():
    spec = SERIES_TYPE_SPECS[SeriesType.COLORMAP]
    assert spec.marker_mode == "required"
    assert spec.supports_line_style is False
    assert spec.supports_color is False
    assert spec.supports_fill is False
    assert spec.supports_error_bars is False
    assert spec.needs_x_column is True
    assert spec.needs_secondary_columns is False
    assert spec.needs_z_column is True
    assert spec.supports_gridding is False


def test_heatmap_series_spec():
    spec = SERIES_TYPE_SPECS[SeriesType.HEATMAP]
    assert spec.marker_mode == "unsupported"
    assert spec.supports_line_style is False
    assert spec.supports_color is False
    assert spec.supports_fill is False
    assert spec.supports_error_bars is False
    assert spec.needs_x_column is True
    assert spec.needs_z_column is True
    assert spec.supports_gridding is True


def test_existing_series_specs_default_new_fields_false():
    from pandaplot.models.chart.series_type import SeriesType as ST
    for st in (ST.LINE, ST.SCATTER, ST.BAR, ST.HIST, ST.VECTOR):
        spec = SERIES_TYPE_SPECS[st]
        assert spec.needs_z_column is False
        assert spec.supports_gridding is False


def test_colormap_chart_type_spec():
    spec = CHART_TYPE_SPECS[ChartType.COLORMAP]
    assert spec.roles == ("x", "y", "z")
    assert spec.required_roles == ("x", "y", "z")
    # A Colormap chart may also hold plain Scatter/Line series alongside its
    # color-mapped points -- e.g. an overlay of raw data points or a trend
    # line -- not just SeriesType.COLORMAP series.
    assert spec.allowed_series_types == frozenset({SeriesType.COLORMAP, SeriesType.SCATTER, SeriesType.LINE})
    assert spec.allows_fit is False
    assert spec.default_series_type == SeriesType.COLORMAP


def test_heatmap_chart_type_spec():
    spec = CHART_TYPE_SPECS[ChartType.HEATMAP]
    assert spec.roles == ("x", "y", "z")
    assert spec.required_roles == ("x", "y", "z")
    # A Heatmap chart may also hold plain Scatter/Line series alongside its
    # gridded matrix -- e.g. marking specific points or overlaying a trend
    # line -- not just SeriesType.HEATMAP series.
    assert spec.allowed_series_types == frozenset({SeriesType.HEATMAP, SeriesType.SCATTER, SeriesType.LINE})
    assert spec.allows_fit is False
    assert spec.default_series_type == SeriesType.HEATMAP


def test_colormap_and_heatmap_charts_can_add_scatter_and_line_series():
    """The 'add series' dropdown in the Data tab lists spec.allowed_series_
    types for the chart's current type (data_tab.py's _rebuild_series_type_
    options-equivalent) -- widening this set is what actually surfaces
    Scatter/Line as pickable series types on a Colormap/Heatmap chart."""
    for chart_type in (ChartType.COLORMAP, ChartType.HEATMAP):
        allowed = CHART_TYPE_SPECS[chart_type].allowed_series_types
        assert SeriesType.SCATTER in allowed
        assert SeriesType.LINE in allowed
        # Still excludes types that make no sense here (Bar, Hist, Vector,
        # and the *other* color-mapped type).
        assert SeriesType.BAR not in allowed
        assert SeriesType.HIST not in allowed
        assert SeriesType.VECTOR not in allowed
