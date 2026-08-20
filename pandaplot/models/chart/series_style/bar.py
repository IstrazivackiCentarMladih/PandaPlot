"""Style fields for a "bar" series -- color only, plus error bars
(BarSeriesStyle is the one non-marker-capable type that still supports
them -- see SeriesTypeSpec.supports_error_bars)."""
from dataclasses import dataclass, field

from pandaplot.models.chart.error_bar_config import ErrorBarConfig
from pandaplot.models.chart.series_style.base import SeriesStyleBase


@dataclass
class BarSeriesStyle(SeriesStyleBase):
    color: str = "#1f77b4"
    error_bars: ErrorBarConfig = field(default_factory=ErrorBarConfig)
