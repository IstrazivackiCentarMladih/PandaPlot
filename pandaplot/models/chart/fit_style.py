"""Style fields for a curve fit's line and confidence band.

Deliberately does NOT subclass LineSeriesStyle: a fit has no marker
concept at all (see StyleTab.load_fit_style's own docstring), and its
"fill" is a confidence band drawn AROUND the curve (from
FitData.confidence_lower/confidence_upper), not an area-fill-to-baseline
UNDER it like DataSeries's fill_* fields -- different semantics, needing
different fields (band_fill_alpha/band_color vs fill_color/fill_alpha/
fill_orientation/fill_base/fill_to_index). Inheriting LineSeriesStyle
would resurrect exactly the "carries fields it never uses" problem the
per-series-type style split (SeriesStyleBase subclasses) exists to avoid.
"""
from dataclasses import dataclass

from pandaplot.models.chart.series_style.base import SeriesStyleBase


@dataclass
class FitStyle(SeriesStyleBase):
    color: str = "#ff7f0e"
    line_style: str = "dashed"
    line_width: float = 2.0
    alpha: float = 1.0
    band_fill_enabled: bool = True
    band_fill_alpha: float = 0.2
    band_color: str = ""  # "" => inherit the fit line's own color
