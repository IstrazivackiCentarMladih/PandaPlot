"""Style fields for a "colormap" series -- a color-mapped scatter, where
Z (picked on the Data tab) drives point color through a colormap instead
of a fixed `color`. Marker shape/size/edge still apply (marker_mode is
"required", like scatter); render_colormap_series() (series_renderers/
colormap.py) reads marker fields for everything except fill color, which
comes from z_data.

The colormap name and color-scale limits are NOT here: there's only ever
one physical colorbar drawn for a whole chart (chart_editor.py), so they
live on Chart.config instead, shared across every Colormap/Heatmap series
on the chart. See
docs/superpowers/specs/2026-08-21-shared-chart-level-color-map-design.md."""
from dataclasses import dataclass, field

from pandaplot.models.chart.marker_style import MarkerStyle
from pandaplot.models.chart.series_style.base import SeriesStyleBase


@dataclass
class ColormapSeriesStyle(SeriesStyleBase):
    z_column_id: str = ""
    z_column: str = ""
    marker: MarkerStyle = field(default_factory=MarkerStyle)

    @property
    def swatch_color(self) -> str:
        return self.marker.marker_color
