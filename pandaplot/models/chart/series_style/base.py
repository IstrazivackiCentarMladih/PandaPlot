"""Common base for per-series-type style dataclasses.

Deliberately empty -- each concrete style class (line.py/scatter.py/...)
declares only the fields its own series type actually uses, so a
BarSeriesStyle never carries an unused line_width field the way today's
flat DataSeries carries vector fields on a line series. This class exists
purely so DataSeries.style can be typed as SeriesStyleBase and so
SeriesTypeSpec.style_cls has a common bound (type[SeriesStyleBase]).
"""
from dataclasses import dataclass


@dataclass
class SeriesStyleBase:
    pass
