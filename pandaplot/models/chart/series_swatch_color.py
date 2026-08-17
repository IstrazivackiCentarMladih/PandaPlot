"""Type-aware "what single color represents this series" helper, for UI
swatches (e.g. data_tab.py's per-series color square). VectorSeriesStyle
has no `color` field -- only `vector_color` -- so callers that don't care
about the distinction can use this instead of branching inline."""
from pandaplot.models.chart.series_style import VectorSeriesStyle


def series_swatch_color(series) -> str:
    style = series.style
    if isinstance(style, VectorSeriesStyle):
        return style.vector_color
    return style.color
