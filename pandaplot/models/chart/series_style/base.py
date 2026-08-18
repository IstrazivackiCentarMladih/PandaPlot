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
    """Common base for every per-series-type style dataclass. Deliberately
    holds no fields of its own -- exists only so DataSeries.style can be
    typed against a common bound and SeriesTypeSpec.style_cls has a
    shared type to reference.
    """

    @property
    def swatch_color(self) -> str:
        """The single color that best represents this style, for UI
        swatches (e.g. data_tab.py's per-series color square). Overridden
        by VectorSeriesStyle, which has no `color` field -- only
        `vector_color`."""
        return self.color  # type: ignore[attr-defined]
