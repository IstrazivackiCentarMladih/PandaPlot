"""Pure-matplotlib tests for applying Chart.style background colors to a
Figure/Axes pair, independent of Qt (mirrors test_chart_editor_title_helpers.py)."""
from matplotlib.figure import Figure


def apply_background_colors(fig, axes, figure_color, axes_color):
    """Mirrors the snippet added to ChartEditor.update_chart."""
    fig.set_facecolor(figure_color if figure_color is not None else "none")
    axes.set_facecolor(axes_color if axes_color is not None else "none")


def test_apply_background_colors_sets_solid_colors():
    fig = Figure()
    axes = fig.add_subplot(111)
    apply_background_colors(fig, axes, "#ff0000", "#00ff00")
    assert fig.get_facecolor() == (1.0, 0.0, 0.0, 1.0)
    assert axes.get_facecolor() == (0.0, 1.0, 0.0, 1.0)


def test_apply_background_colors_none_means_transparent():
    fig = Figure()
    axes = fig.add_subplot(111)
    apply_background_colors(fig, axes, None, None)
    assert fig.get_facecolor()[3] == 0.0
    assert axes.get_facecolor()[3] == 0.0


def test_apply_background_colors_independently_configurable():
    fig = Figure()
    axes = fig.add_subplot(111)
    apply_background_colors(fig, axes, "#ff0000", None)
    assert fig.get_facecolor() == (1.0, 0.0, 0.0, 1.0)
    assert axes.get_facecolor()[3] == 0.0
