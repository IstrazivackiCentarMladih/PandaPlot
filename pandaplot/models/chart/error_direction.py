"""Which side(s) of a data point a symmetric error bar's magnitude is
drawn on. Lives here (not in models/project/items/chart.py, where it
used to be defined) so ErrorBarConfig (models/chart/error_bar_config.py)
can depend on it without an import cycle back into chart.py, which
itself depends on the series_style package that composes ErrorBarConfig.
"""
from enum import StrEnum


class ErrorDirection(StrEnum):
    BOTH = "both"
    PLUS = "plus"
    MINUS = "minus"
