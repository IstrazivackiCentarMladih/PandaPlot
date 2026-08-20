"""Style fields for a "hist" series -- render_hist_series() in
pandaplot/gui/components/tabs/chart/series_renderers/hist.py reads only
color (bin count is chart-level config, not a per-series style field)."""
from dataclasses import dataclass

from pandaplot.models.chart.series_style.base import SeriesStyleBase


@dataclass
class HistSeriesStyle(SeriesStyleBase):
    color: str = "#1f77b4"
