"""Style fields for a "line" series -- the only type that reads
line_style/line_width/fill_* in chart_editor.py's update_chart()
(lines 818-852)."""
from dataclasses import dataclass

from pandaplot.models.chart.series_style.base import SeriesStyleBase


@dataclass
class LineSeriesStyle(SeriesStyleBase):
    color: str = "#1f77b4"
    marker_color: str = ""
    marker_edge_color: str = "#000000"
    marker_edge_width: float = 1.0
    line_style: str = "solid"
    marker_style: str = "circle"
    line_width: float = 2.0
    marker_size: float = 2.0
    fill_enabled: bool = False
    fill_color: str = ""
    fill_alpha: float = 0.3
    fill_orientation: str = "vertical"
    fill_base: float = 0.0
    fill_to_index: int = -1
