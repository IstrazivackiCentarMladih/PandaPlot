"""Style fields for a "bar" series -- chart_editor.py's bar branch
(lines 864-868) reads only color (plus the shared alpha, which stays a
top-level DataSeries field, not per-type)."""
from dataclasses import dataclass

from pandaplot.models.chart.series_style.base import SeriesStyleBase


@dataclass
class BarSeriesStyle(SeriesStyleBase):
    color: str = "#1f77b4"
