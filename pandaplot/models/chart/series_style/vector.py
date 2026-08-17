"""Style fields for a "vector" series -- chart_editor.py's vector branch
(lines 874-892) reads these plus u/v/magnitude column references, which
stay on DataSeries directly (they're column refs, not appearance, same
treatment as x_column_id/y_column_id)."""
from dataclasses import dataclass

from pandaplot.models.chart.series_style.base import SeriesStyleBase


@dataclass
class VectorSeriesStyle(SeriesStyleBase):
    vector_color: str = "#1f77b4"
    vector_colormap: str = ""
    vector_scale: float = 0.0
    vector_width: float = 0.005
    vector_head_width: float = 3.0
    vector_head_length: float = 5.0
    vector_head_axis_length: float = 4.5
