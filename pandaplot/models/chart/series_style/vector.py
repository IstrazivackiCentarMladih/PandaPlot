"""Style fields for a "vector" series -- chart_editor.py's vector branch
(lines 874-892) reads these plus u/v/magnitude column references, now
composed here on VectorSeriesStyle (moved off DataSeries since only a
VECTOR series ever has them)."""
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
    # Column references -- moved here from DataSeries, since only a
    # VECTOR series ever has these (mirrors why marker fields only exist
    # on marker-capable style classes, not as always-present-but-unused
    # fields on the shared DataSeries envelope).
    u_column_id: str = ""
    v_column_id: str = ""
    u_column: str = ""
    v_column: str = ""
    magnitude_column_id: str = ""
    magnitude_column: str = ""
