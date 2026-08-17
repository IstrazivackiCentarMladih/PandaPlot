"""Style fields for a "scatter" series -- chart_editor.py's scatter
branch (lines 853-863) reads only marker fields, never line_style/
line_width/fill_*."""
from dataclasses import dataclass

from pandaplot.models.chart.series_style.base import SeriesStyleBase


@dataclass
class ScatterSeriesStyle(SeriesStyleBase):
    color: str = "#1f77b4"
    marker_color: str = ""
    marker_edge_color: str = "#000000"
    marker_edge_width: float = 1.0
    marker_style: str = "circle"
    marker_size: float = 2.0
