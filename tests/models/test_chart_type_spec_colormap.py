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
    assert spec.allowed_series_types == frozenset({SeriesType.COLORMAP})
    assert spec.allows_fit is False
    assert spec.default_series_type == SeriesType.COLORMAP


def test_heatmap_chart_type_spec():
    spec = CHART_TYPE_SPECS[ChartType.HEATMAP]
    assert spec.roles == ("x", "y", "z")
    assert spec.required_roles == ("x", "y", "z")
    assert spec.allowed_series_types == frozenset({SeriesType.HEATMAP})
    assert spec.allows_fit is False
    assert spec.default_series_type == SeriesType.HEATMAP
