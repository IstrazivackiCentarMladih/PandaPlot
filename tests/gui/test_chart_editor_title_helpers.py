"""
Unit tests for apply_chart_title(), the pure title/subtitle helper used by
ChartEditorWidget.update_chart(). Exercised against a real matplotlib Axes
(no Qt/QApplication involved), same pattern as test_chart_editor_tick_helpers.py.
"""

import matplotlib

matplotlib.use("Agg")

from matplotlib.figure import Figure

from pandaplot.gui.components.tabs.chart.chart_editor import apply_chart_title


def _make_axes():
    fig = Figure()
    return fig.add_subplot(111)


def test_sets_title_text_and_font_size():
    axes = _make_axes()
    apply_chart_title(axes, title="My Chart", subtitle="", title_font_size=18)
    assert axes.get_title() == "My Chart"
    assert axes.title.get_fontsize() == 18


def test_empty_subtitle_produces_no_second_line():
    axes = _make_axes()
    apply_chart_title(axes, title="My Chart", subtitle="", title_font_size=14)
    assert "\n" not in axes.get_title()


def test_non_empty_subtitle_is_appended_on_a_second_line():
    axes = _make_axes()
    apply_chart_title(axes, title="My Chart", subtitle="n = 42", title_font_size=14)
    assert axes.get_title() == "My Chart\nn = 42"
