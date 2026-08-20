"""Style fields for a "colormap" series -- a color-mapped scatter, where
Z (picked on the Data tab) drives point color through `colormap` instead
of a fixed `color`. Marker shape/size/edge still apply (marker_mode is
"required", like scatter); render_colormap_series() (series_renderers/
colormap.py) reads marker fields for everything except fill color, which
comes from z_data via colormap/color_vmin/color_vmax."""
from dataclasses import dataclass, field

from pandaplot.models.chart.marker_style import MarkerStyle
from pandaplot.models.chart.series_style.base import SeriesStyleBase


@dataclass
class ColormapSeriesStyle(SeriesStyleBase):
    z_column_id: str = ""
    z_column: str = ""
    colormap: str = "viridis"
    colorbar_show: bool = True
    colorbar_label: str = ""
    color_scale_auto: bool = True
    color_vmin: float = 0.0
    color_vmax: float = 1.0
    marker: MarkerStyle = field(default_factory=MarkerStyle)

    @property
    def swatch_color(self) -> str:
        return self.marker.marker_color
