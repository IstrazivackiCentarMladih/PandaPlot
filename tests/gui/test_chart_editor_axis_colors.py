"""Pure-matplotlib tests for apply_axis_ticks color params and apply_spine_colors."""
from matplotlib.figure import Figure

from pandaplot.gui.components.tabs.chart.chart_editor import apply_axis_ticks, apply_spine_colors


def test_apply_axis_ticks_sets_major_and_minor_tick_colors():
    fig = Figure()
    axes = fig.add_subplot(111)
    apply_axis_ticks(
        axes.xaxis, "auto", 5, 1.0, "auto", "",
        minor_enabled=True, major_color="#ff0000", minor_color="#00ff00")
    major_params = axes.xaxis.get_tick_params(which="major")
    minor_params = axes.xaxis.get_tick_params(which="minor")
    assert major_params["color"] == "#ff0000"
    assert minor_params["color"] == "#00ff00"


def test_apply_spine_colors_without_secondary_axis():
    fig = Figure()
    axes = fig.add_subplot(111)
    apply_spine_colors(axes, None, "#ff0000", "#00ff00", "#0000ff")
    assert axes.spines["bottom"].get_edgecolor() == (1.0, 0.0, 0.0, 1.0)
    assert axes.spines["top"].get_edgecolor() == (1.0, 0.0, 0.0, 1.0)
    assert axes.spines["left"].get_edgecolor() == (0.0, 1.0, 0.0, 1.0)
    assert axes.spines["right"].get_edgecolor() == (0.0, 1.0, 0.0, 1.0)


def test_apply_spine_colors_right_spine_follows_y2_when_present():
    fig = Figure()
    axes = fig.add_subplot(111)
    axes2 = axes.twinx()
    apply_spine_colors(axes, axes2, "#ff0000", "#00ff00", "#0000ff")
    assert axes.spines["right"].get_edgecolor() == (0.0, 1.0, 0.0, 1.0)
    assert axes2.spines["right"].get_edgecolor() == (0.0, 0.0, 1.0, 1.0)


def test_apply_spine_colors_mirrors_x_y_onto_secondary_axis_spines():
    # Regression test: axes2 (twinx()) draws its own full spine box on top
    # of axes, so its bottom/top/left spines must be kept in sync with
    # axes's x/y colors, or they silently paint over them with black.
    fig = Figure()
    axes = fig.add_subplot(111)
    axes2 = axes.twinx()
    apply_spine_colors(axes, axes2, "#ff0000", "#00ff00", "#0000ff")
    assert axes2.spines["bottom"].get_edgecolor() == (1.0, 0.0, 0.0, 1.0)
    assert axes2.spines["top"].get_edgecolor() == (1.0, 0.0, 0.0, 1.0)
    assert axes2.spines["left"].get_edgecolor() == (0.0, 1.0, 0.0, 1.0)
