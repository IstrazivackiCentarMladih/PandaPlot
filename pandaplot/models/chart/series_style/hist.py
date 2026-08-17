"""Style fields for a "hist" series -- chart_editor.py's hist branch
(lines 869-873) reads only color (bin count is chart-level config, not a
per-series style field)."""
from dataclasses import dataclass

from pandaplot.models.chart.series_style.base import SeriesStyleBase


@dataclass
class HistSeriesStyle(SeriesStyleBase):
    color: str = "#1f77b4"
