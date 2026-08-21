"""Renders a "colormap" series: a scatter whose fill color is driven by
series_data.z_data through style.colormap, not a fixed color -- marker
shape/size/edge still come from style.marker (marker_mode is "required"
for this type). Returns the matplotlib PathCollection so chart_editor.py
can attach the shared colorbar to it.

Edge color has no single style.color to fall back to here (unlike line.py/
scatter.py) since fill genuinely varies per point -- an empty
marker_edge_color instead resolves to matplotlib's "face" sentinel, which
makes each point's edge match ITS OWN fill exactly, point by point."""
from pandaplot.gui.components.tabs.chart.chart_heatmap import resolve_color_limits
from pandaplot.gui.components.tabs.chart.series_data import SeriesData
from pandaplot.gui.components.tabs.chart.style_maps import MARKER_MAP
from pandaplot.models.chart.series_style import ColormapSeriesStyle


def render_colormap_series(axes, series_data: SeriesData, style: ColormapSeriesStyle,
                            label: str, alpha: float, visible: bool, extra: dict):
    vmin, vmax = resolve_color_limits(
        series_data.z_data, style.color_scale_auto, style.color_vmin, style.color_vmax)
    return axes.scatter(
        series_data.x_data, series_data.y_data,
        c=series_data.z_data, cmap=style.colormap, vmin=vmin, vmax=vmax,
        marker=MARKER_MAP.get(style.marker.marker_style, "o"),
        s=style.marker.marker_size ** 2,
        edgecolors=style.marker.marker_edge_color or "face",
        linewidths=style.marker.marker_edge_width,
        label=label, alpha=alpha)
