"""Style fields for a "scatter" series -- marker fields only, no line/
fill; chart_editor.py's scatter branch reads only marker fields."""
from dataclasses import dataclass, field

from pandaplot.models.chart.error_bar_config import ErrorBarConfig
from pandaplot.models.chart.marker_style import MarkerStyle
from pandaplot.models.chart.series_style.base import SeriesStyleBase


@dataclass
class ScatterSeriesStyle(SeriesStyleBase):
    color: str = "#1f77b4"
    marker: MarkerStyle = field(default_factory=MarkerStyle)
    error_bars: ErrorBarConfig = field(default_factory=ErrorBarConfig)
