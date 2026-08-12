"""Unit tests for apply_tick_label_font(), the pure helper that sets
font family/size/weight/style on every major and minor tick-value label of
a matplotlib Axis (tick_params can't carry font-family/weight/style, so
these must be set directly on each Text artist)."""
from matplotlib.figure import Figure

from pandaplot.gui.components.tabs.chart.chart_editor import apply_axis_ticks, apply_tick_label_font


def _make_axis():
    fig = Figure()
    ax = fig.add_subplot(111)
    ax.set_xlim(0, 10)
    return ax.xaxis


def test_sets_font_family_size_on_major_tick_labels():
    axis = _make_axis()
    apply_axis_ticks(axis, "auto", 5, 1.0, "auto", "")
    apply_tick_label_font(axis, font_size=14, font_family="Georgia", bold=False, italic=False)
    labels = [label for label in axis.get_ticklabels() if label.get_text()]
    assert labels, "expected at least one tick label after autoscale"
    for label in labels:
        assert label.get_fontfamily() == ["Georgia"]
        assert label.get_fontsize() == 14


def test_bold_and_italic_are_applied_to_tick_labels():
    axis = _make_axis()
    apply_axis_ticks(axis, "auto", 5, 1.0, "auto", "")
    apply_tick_label_font(axis, font_size=10, font_family="DejaVu Sans", bold=True, italic=True)
    labels = [label for label in axis.get_ticklabels() if label.get_text()]
    for label in labels:
        assert label.get_fontweight() == "bold"
        assert label.get_fontstyle() == "italic"


def test_minor_tick_labels_also_get_the_font():
    axis = _make_axis()
    apply_axis_ticks(axis, "auto", 5, 1.0, "auto", "", minor_enabled=True)
    apply_tick_label_font(axis, font_size=8, font_family="Georgia", bold=False, italic=False)
    minor_labels = [label for label in axis.get_ticklabels(minor=True) if label.get_text()]
    for label in minor_labels:
        assert label.get_fontfamily() == ["Georgia"]


def test_rotation_defaults_to_zero():
    axis = _make_axis()
    apply_axis_ticks(axis, "auto", 5, 1.0, "auto", "")
    apply_tick_label_font(axis, font_size=10, font_family="DejaVu Sans")
    labels = [label for label in axis.get_ticklabels() if label.get_text()]
    for label in labels:
        assert label.get_rotation() == 0


def test_rotation_is_applied_to_major_and_minor_tick_labels():
    axis = _make_axis()
    apply_axis_ticks(axis, "auto", 5, 1.0, "auto", "", minor_enabled=True)
    apply_tick_label_font(axis, font_size=10, font_family="DejaVu Sans", rotation=45)
    labels = [label for label in axis.get_ticklabels() + axis.get_ticklabels(minor=True) if label.get_text()]
    assert labels, "expected at least one tick label after autoscale"
    for label in labels:
        assert label.get_rotation() == 45
