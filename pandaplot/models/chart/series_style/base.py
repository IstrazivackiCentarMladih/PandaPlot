"""Common base for per-series-type style dataclasses.

Deliberately holds no data fields of its own -- each concrete style class
(line.py/scatter.py/...) declares only the fields its own series type
actually uses, so a BarSeriesStyle never carries an unused line_width
field the way DataSeries USED TO carry vector fields on a line series
back when it was one flat dataclass. This class exists purely so
DataSeries.style can be typed as SeriesStyleBase and so
SeriesTypeSpec.style_cls has a common bound (type[SeriesStyleBase]).
"""
from dataclasses import dataclass


@dataclass
class SeriesStyleBase:
    """Common base for every per-series-type style dataclass. Deliberately
    holds no data fields of its own -- it does define a `swatch_color`
    property, which is fine (properties aren't fields) -- exists only so
    DataSeries.style can be typed against a common bound and
    SeriesTypeSpec.style_cls has a shared type to reference.
    """

    @property
    def swatch_color(self) -> str:
        """The single color that best represents this style, for UI
        swatches (e.g. data_tab.py's per-series color square). Overridden
        by VectorSeriesStyle, which has no `color` field -- only
        `vector_color`."""
        return self.color  # type: ignore[attr-defined]
