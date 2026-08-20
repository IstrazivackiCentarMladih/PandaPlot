"""Marker (point-symbol) styling, shared by every series type whose
marker_mode is not "unsupported" (today: LINE, SCATTER). Extracted from
LineSeriesStyle/ScatterSeriesStyle, which used to declare these 5 fields
identically -- composition here means a future third marker-capable
series type reuses this instead of copying the fields again.
"""
from dataclasses import dataclass


@dataclass
class MarkerStyle:
    marker_color: str = ""
    marker_edge_color: str = "#000000"
    marker_edge_width: float = 1.0
    marker_style: str = "circle"
    marker_size: float = 2.0
