"""Chart styling enums shared across the sidebar tabs.

Historically also held ChartType and a full ChartConfiguration/LineStyle/
MarkerStyle/AxisStyle/LegendStyle dataclass tree, superseded by
Chart.config/Chart.style (plain dicts) and never instantiated outside this
file's own from_dict -- those are deleted. ChartType itself moved to
pandaplot/models/chart/chart_type.py (see chart_tab.py/style_tab.py). Only
the enums below are still live: LineStyleType/MarkerType back the Style
tab's line/marker controls, ScaleType/LegendPosition back the Axes/Legend
tabs.
"""

from enum import Enum


class LineStyleType(Enum):
    """Line style types."""
    SOLID = "solid"
    DASHED = "dashed"
    DOTTED = "dotted"
    DASHDOT = "dashdot"
    NONE = "none"


class MarkerType(Enum):
    """Marker types."""
    CIRCLE = "circle"
    SQUARE = "square"
    TRIANGLE = "triangle"
    DIAMOND = "diamond"
    STAR = "star"
    PLUS = "plus"
    CROSS = "cross"
    NONE = "none"


class ScaleType(Enum):
    """Axis scale types."""
    LINEAR = "linear"
    LOG = "log"


class LegendPosition(Enum):
    """Legend position options."""
    UPPER_RIGHT = "upper right"
    UPPER_LEFT = "upper left"
    LOWER_RIGHT = "lower right"
    LOWER_LEFT = "lower left"
    CENTER = "center"
    UPPER_CENTER = "upper center"
    LOWER_CENTER = "lower center"
    CENTER_LEFT = "center left"
    CENTER_RIGHT = "center right"
    BEST = "best"
