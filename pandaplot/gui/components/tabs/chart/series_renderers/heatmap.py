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
    # Note: unlike every other renderer here, `label` is deliberately NOT
    # passed through to pcolormesh. matplotlib's Legend has no handler for
    # QuadMesh (the artist pcolormesh returns) -- passing a label achieves
    # nothing (get_legend_handles_labels() drops it) and only produces a
    # "Legend does not support handles for QuadMesh instances" UserWarning
    # on every render. The real fix for a Heatmap chart's empty legend box
    # is in chart_editor.py: skip axes.legend() entirely when there are no
    # real legend handles, rather than trying to manufacture one here.
    return axes.pcolormesh(
        xs, ys, grid, cmap=style.colormap, vmin=vmin, vmax=vmax,
        shading="nearest", alpha=alpha)
