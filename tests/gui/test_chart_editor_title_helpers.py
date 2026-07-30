"""
Unit tests for apply_chart_title(), the pure title/subtitle helper used by
ChartEditorWidget.update_chart(). Exercised against a real matplotlib Axes
(no Qt/QApplication involved), same pattern as test_chart_editor_tick_helpers.py.

Title renders via fig.suptitle() and subtitle via axes.set_title() (two
separate Matplotlib artists) so each can have an independent font size --
a single set_title() call can't mix font sizes within one string.
"""

import matplotlib

matplotlib.use("Agg")

from matplotlib.figure import Figure

from pandaplot.gui.components.tabs.chart.chart_editor import apply_chart_title


def _make_axes():
    fig = Figure()
    return fig.add_subplot(111)


def test_sets_title_via_figure_suptitle_with_its_own_font_size():
    axes = _make_axes()
    apply_chart_title(axes, title="My Chart", subtitle="", title_font_size=18, subtitle_font_size=12)
    assert axes.figure.get_suptitle() == "My Chart"
    assert axes.figure._suptitle.get_fontsize() == 18


def test_empty_subtitle_clears_the_axes_title():
    axes = _make_axes()
    apply_chart_title(axes, title="My Chart", subtitle="", title_font_size=14, subtitle_font_size=12)
    assert axes.get_title() == ""


def test_non_empty_subtitle_renders_via_axes_title_with_its_own_font_size():
    axes = _make_axes()
    apply_chart_title(axes, title="My Chart", subtitle="n = 42", title_font_size=14, subtitle_font_size=10)
    assert axes.get_title() == "n = 42"
    assert axes.title.get_fontsize() == 10


def test_title_color_is_applied_to_the_suptitle():
    axes = _make_axes()
    apply_chart_title(
        axes, title="My Chart", subtitle="", title_font_size=14, subtitle_font_size=12,
        title_color="#ff0000",
    )
    assert axes.figure._suptitle.get_color() == "#ff0000"


def test_subtitle_color_is_applied_to_the_axes_title():
    axes = _make_axes()
    apply_chart_title(
        axes, title="My Chart", subtitle="n = 42", title_font_size=14, subtitle_font_size=10,
        subtitle_color="#00ff00",
    )
    assert axes.title.get_color() == "#00ff00"


def test_title_and_subtitle_color_default_to_black():
    axes = _make_axes()
    apply_chart_title(axes, title="My Chart", subtitle="n = 42", title_font_size=14, subtitle_font_size=10)
    assert axes.figure._suptitle.get_color() == "#000000"
    assert axes.title.get_color() == "#000000"


def test_title_font_family_is_applied_to_the_suptitle():
    axes = _make_axes()
    apply_chart_title(
        axes, title="My Chart", subtitle="", title_font_size=14, subtitle_font_size=12,
        title_font_family="Georgia",
    )
    assert axes.figure._suptitle.get_fontfamily() == ["Georgia"]


def test_subtitle_font_family_is_applied_to_the_axes_title():
    axes = _make_axes()
    apply_chart_title(
        axes, title="My Chart", subtitle="n = 42", title_font_size=14, subtitle_font_size=10,
        subtitle_font_family="Georgia",
    )
    assert axes.title.get_fontfamily() == ["Georgia"]


def test_title_and_subtitle_font_family_default_to_dejavu_sans():
    axes = _make_axes()
    apply_chart_title(axes, title="My Chart", subtitle="n = 42", title_font_size=14, subtitle_font_size=10)
    assert axes.figure._suptitle.get_fontfamily() == ["DejaVu Sans"]
    assert axes.title.get_fontfamily() == ["DejaVu Sans"]


def test_mathtext_title_text_passes_through_unmodified():
    axes = _make_axes()
    apply_chart_title(axes, title=r"Energy $E = mc^2$", subtitle="", title_font_size=14, subtitle_font_size=12)
    assert axes.figure.get_suptitle() == r"Energy $E = mc^2$"


def test_mathtext_subtitle_text_passes_through_unmodified():
    axes = _make_axes()
    apply_chart_title(axes, title="t", subtitle=r"$\alpha = 0.05$", title_font_size=14, subtitle_font_size=10)
    assert axes.get_title() == r"$\alpha = 0.05$"
