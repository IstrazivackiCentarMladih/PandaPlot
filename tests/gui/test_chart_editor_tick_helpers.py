"""
Unit tests for apply_axis_ticks(), the pure tick-locator/formatter helper
used by ChartEditorWidget.update_chart(). Exercised against a real
matplotlib Axis (no Qt/QApplication involved).
"""

import matplotlib
matplotlib.use("Agg")  # headless backend, no display/Qt required

from matplotlib.figure import Figure
from matplotlib.ticker import FuncFormatter, MaxNLocator, MultipleLocator

from pandaplot.gui.components.tabs.chart.chart_editor import apply_axis_ticks


def _make_axis():
    fig = Figure()
    ax = fig.add_subplot(111)
    return ax.xaxis


def test_auto_mode_leaves_default_locator_untouched():
    axis = _make_axis()
    default_locator = axis.get_major_locator()
    apply_axis_ticks(axis, "auto", count=5, step=1.0, fmt="auto", custom_fmt="")
    assert axis.get_major_locator() is default_locator


def test_count_mode_sets_max_n_locator():
    axis = _make_axis()
    apply_axis_ticks(axis, "count", count=8, step=1.0, fmt="auto", custom_fmt="")
    locator = axis.get_major_locator()
    assert isinstance(locator, MaxNLocator)


def test_step_mode_sets_multiple_locator():
    axis = _make_axis()
    apply_axis_ticks(axis, "step", count=5, step=2.5, fmt="auto", custom_fmt="")
    locator = axis.get_major_locator()
    assert isinstance(locator, MultipleLocator)


def test_integer_format_renders_whole_numbers():
    axis = _make_axis()
    apply_axis_ticks(axis, "auto", count=5, step=1.0, fmt="integer", custom_fmt="")
    formatter = axis.get_major_formatter()
    assert isinstance(formatter, FuncFormatter)
    assert formatter(3.7, 0) == "4"


def test_two_decimal_format():
    axis = _make_axis()
    apply_axis_ticks(axis, "auto", count=5, step=1.0, fmt="2decimal", custom_fmt="")
    formatter = axis.get_major_formatter()
    assert formatter(3.14159, 0) == "3.14"


def test_scientific_format():
    axis = _make_axis()
    apply_axis_ticks(axis, "auto", count=5, step=1.0, fmt="scientific", custom_fmt="")
    formatter = axis.get_major_formatter()
    assert formatter(1234.5, 0) == "1.23e+03"


def test_valid_custom_format_is_applied():
    axis = _make_axis()
    apply_axis_ticks(axis, "auto", count=5, step=1.0, fmt="custom", custom_fmt="{:.1f}kg")
    formatter = axis.get_major_formatter()
    assert formatter(2.0, 0) == "2.0kg"


def test_invalid_custom_format_falls_back_to_plain_number_instead_of_raising():
    axis = _make_axis()
    apply_axis_ticks(axis, "auto", count=5, step=1.0, fmt="custom", custom_fmt="{:z}")
    formatter = axis.get_major_formatter()
    assert formatter(2.0, 0) == "2.0"
