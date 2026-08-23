"""Marker (point-symbol) styling, shared by every series type whose
marker_mode is not "unsupported" (today: LINE, SCATTER, COLORMAP).
Extracted from LineSeriesStyle/ScatterSeriesStyle, which used to declare
these 5 fields identically -- composition here means a future third
marker-capable series type reuses this instead of copying the fields
again.

`marker_edge_color` defaults to "" (empty), the same "inherit" sentinel
`marker_color` already uses: every renderer that reads these fields
(line.py/scatter.py fall back to `style.color`; colormap.py falls back to
matplotlib's "face" sentinel, matching each point's own fill) treats an
empty edge color as "match the fill" rather than a literal color. A fresh
series therefore starts with a matching fill/edge by default -- still
independently editable afterward via the Style tab's marker controls.
"""
from dataclasses import dataclass


@dataclass
class MarkerStyle:
    marker_color: str = ""
    marker_edge_color: str = ""
    marker_edge_width: float = 1.0
    marker_style: str = "circle"
    marker_size: float = 2.0
