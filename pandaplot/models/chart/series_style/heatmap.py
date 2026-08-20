"""Style fields for a "heatmap" series -- a gridded matrix drawn with
pcolormesh. No marker/line/fill fields (marker_mode is "unsupported");
render_heatmap_series() (series_renderers/heatmap.py) reads only these
plus x/y/z data. `heatmap_gridding`/`heatmap_resolution` control how
scattered (x, y, z) points become a regular grid -- see chart_heatmap.py."""
from dataclasses import dataclass

from pandaplot.models.chart.series_style.base import SeriesStyleBase


@dataclass
class HeatmapSeriesStyle(SeriesStyleBase):
    z_column_id: str = ""
    z_column: str = ""
    colormap: str = "viridis"
    colorbar_show: bool = True
    colorbar_label: str = ""
    color_scale_auto: bool = True
    color_vmin: float = 0.0
    color_vmax: float = 1.0
    heatmap_gridding: str = "grid"  # "grid" | "binned" | "interpolated"
    heatmap_resolution: int = 50

    @property
    def swatch_color(self) -> str:
        return ""
