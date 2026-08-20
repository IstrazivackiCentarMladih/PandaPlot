"""Renders a "heatmap" series: (x, y, z) gridded via
chart_heatmap.build_heatmap_grid (mode = style.heatmap_gridding) and drawn
with pcolormesh. Returns None (not a mappable) when there's no data to
grid, so the caller can skip the colorbar and surface a per-series error
instead of drawing an empty axes."""
from pandaplot.gui.components.tabs.chart.chart_heatmap import (
    build_heatmap_grid,
    resolve_color_limits,
)
from pandaplot.gui.components.tabs.chart.series_data import SeriesData
from pandaplot.models.chart.series_style import HeatmapSeriesStyle


def render_heatmap_series(axes, series_data: SeriesData, style: HeatmapSeriesStyle,
                           label: str, alpha: float, visible: bool, extra: dict):
    vmin, vmax = resolve_color_limits(
        series_data.z_data, style.color_scale_auto, style.color_vmin, style.color_vmax)
    try:
        xs, ys, grid = build_heatmap_grid(
            series_data.x_data, series_data.y_data, series_data.z_data,
            style.heatmap_gridding, style.heatmap_resolution)
    except ValueError:
        return None
    return axes.pcolormesh(
        xs, ys, grid, cmap=style.colormap, vmin=vmin, vmax=vmax,
        shading="nearest", alpha=alpha)
