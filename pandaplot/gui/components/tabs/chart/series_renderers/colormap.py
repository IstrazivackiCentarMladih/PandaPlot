"""Renders a "colormap" series: a scatter whose fill color is driven by
series_data.z_data through a colormap, not a fixed color -- marker
shape/size/edge still come from style.marker (marker_mode is "required"
for this type). Returns the matplotlib PathCollection so chart_editor.py
can attach the shared colorbar to it.

The colormap name and color-scale limits are shared across every
Colormap/Heatmap series on the chart (there's only one physical colorbar)
-- chart_editor.py computes them once and passes them through `extra`
rather than this reading them off `style`.

Edge color has no single style.color to fall back to here (unlike line.py/
scatter.py) since fill genuinely varies per point -- an empty
marker_edge_color instead resolves to matplotlib's "face" sentinel, which
makes each point's edge match ITS OWN fill exactly, point by point.

The Data tab's Z-column picker permits any column, including non-numeric
ones -- passing raw strings straight to scatter(c=...) either raises (a
ValueError matplotlib itself throws, uncaught by anything in
chart_editor.py's render loop, which would blank the WHOLE chart) or,
worse, silently treats valid color-name strings as literal marker colors
instead of values to map through the colormap. Z is coerced to numeric
here and this returns None (matching render_heatmap_series' contract) for
invalid or empty data, so chart_editor.py surfaces a per-series error
instead."""
import numpy as np

from pandaplot.gui.components.tabs.chart.series_data import SeriesData
from pandaplot.gui.components.tabs.chart.style_maps import MARKER_MAP
from pandaplot.models.chart.series_style import ColormapSeriesStyle


def render_colormap_series(axes, series_data: SeriesData, style: ColormapSeriesStyle,
                            label: str, alpha: float, visible: bool, extra: dict):
    try:
        z_data = np.asarray(series_data.z_data, dtype=float)
    except (ValueError, TypeError):
        return None
    if z_data.size == 0:
        return None
    vmin, vmax = extra["color_limits"]
    return axes.scatter(
        series_data.x_data, series_data.y_data,
        c=z_data, cmap=extra["colormap"], vmin=vmin, vmax=vmax,
        marker=MARKER_MAP.get(style.marker.marker_style, "o"),
        s=style.marker.marker_size ** 2,
        edgecolors=style.marker.marker_edge_color or "face",
        linewidths=style.marker.marker_edge_width,
        label=label, alpha=alpha)
