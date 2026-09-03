"""Renders a "bar" series -- color only."""
from pandaplot.gui.components.tabs.chart.series_data import SeriesData
from pandaplot.models.chart.series_style import BarSeriesStyle


def render_bar_series(axes, series_data: SeriesData, style: BarSeriesStyle,
                       label: str, alpha: float, *, visible: bool, extra: dict) -> None:
    bars = axes.bar(series_data.x_data, series_data.y_data,
                     color=style.color,
                     label=label,
                     alpha=alpha)
    if style.show_value_labels:
        # bar_label() places one label per bar, above (or below, for a
        # negative height) it -- unlike line/scatter's point-by-point
        # annotate() loop (series_renderers/value_labels.py), matplotlib
        # already positions these correctly from the BarContainer itself.
        axes.bar_label(bars, fmt="%.3g", fontsize=8)
