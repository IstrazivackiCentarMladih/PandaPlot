"""Style fields for a "line" series -- the only type that reads
line_style/line_width/fill_* in render_line_series()
(pandaplot/gui/components/tabs/chart/series_renderers/line.py)."""
from dataclasses import dataclass, field

from pandaplot.models.chart.error_bar_config import ErrorBarConfig
from pandaplot.models.chart.marker_style import MarkerStyle
from pandaplot.models.chart.series_style.base import SeriesStyleBase


@dataclass
class LineSeriesStyle(SeriesStyleBase):
    color: str = "#1f77b4"
    line_style: str = "solid"
    line_width: float = 2.0
    fill_enabled: bool = False
    fill_color: str = ""
    fill_alpha: float = 0.3
    fill_orientation: str = "vertical"
    fill_base: float = 0.0
    fill_to_index: int = -1
    marker: MarkerStyle = field(default_factory=MarkerStyle)
    error_bars: ErrorBarConfig = field(default_factory=ErrorBarConfig)
