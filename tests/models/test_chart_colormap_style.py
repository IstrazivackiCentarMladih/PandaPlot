from pandaplot.models.chart.series_style import ColormapSeriesStyle, HeatmapSeriesStyle
from pandaplot.models.chart.marker_style import MarkerStyle


def test_colormap_series_style_defaults():
    style = ColormapSeriesStyle()
    assert style.z_column_id == ""
    assert style.z_column == ""
    assert style.colormap == "viridis"
    assert style.colorbar_show is True
    assert style.colorbar_label == ""
    assert style.color_scale_auto is True
    assert style.color_vmin == 0.0
    assert style.color_vmax == 1.0
    assert isinstance(style.marker, MarkerStyle)
    assert style.swatch_color == style.marker.marker_color or style.swatch_color == ""


def test_heatmap_series_style_defaults():
    style = HeatmapSeriesStyle()
    assert style.z_column_id == ""
    assert style.colormap == "viridis"
    assert style.colorbar_show is True
    assert style.color_scale_auto is True
    assert style.heatmap_gridding == "grid"
    assert style.heatmap_resolution == 50


def test_series_types_registered():
    from pandaplot.models.chart.series_type import SeriesType
    assert SeriesType.COLORMAP == "colormap"
    assert SeriesType.HEATMAP == "heatmap"

    from pandaplot.models.chart.chart_type import ChartType
    assert ChartType.COLORMAP == "colormap"
    assert ChartType.HEATMAP == "heatmap"
