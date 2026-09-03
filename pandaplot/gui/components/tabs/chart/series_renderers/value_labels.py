"""Shared helper for annotating each rendered point with its numeric value
(#125), used by the line/scatter renderers -- BarSeriesStyle's own
render_bar_series() uses matplotlib's bar_label() on the BarContainer
axes.bar() returns instead, since that already places one label per bar
correctly positioned above/below it.

Gated by SeriesStyleBase.show_value_labels (declared on LineSeriesStyle/
ScatterSeriesStyle/BarSeriesStyle only) and SeriesTypeSpec.supports_value_labels.
"""
import pandas as pd


def annotate_point_labels(axes, x_data, y_data, *, fontsize: float = 8.0) -> None:
    """Label each (x, y) point with its Y value, offset just above the point.

    Intended for the small datasets the issue this implements (#125) calls
    out (lab reports, a handful of points) -- no cap on point count, since a
    series with too many points to usefully label this way is one a user
    wouldn't turn this on for in the first place.
    """
    for x, y in zip(x_data, y_data, strict=True):
        if pd.isna(x) or pd.isna(y):
            continue
        axes.annotate(
            f"{y:.3g}",
            (x, y),
            textcoords="offset points",
            xytext=(0, 6),
            ha="center",
            fontsize=fontsize,
        )
