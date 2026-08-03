"""Unit tests for resolve_legend_placement(), the pure helper that maps a
legend position (including the new outside/custom options) to matplotlib's
Legend `loc`/`bbox_to_anchor` kwargs."""
from pandaplot.gui.components.tabs.chart.chart_editor import resolve_legend_placement


def test_existing_inside_position_passes_loc_only():
    assert resolve_legend_placement("upper right", 1.02, 0.5, "center left") == {"loc": "upper right"}


def test_outside_right_uses_fixed_loc_and_bbox_anchor():
    result = resolve_legend_placement("outside_right", 1.02, 0.5, "center left")
    assert result == {"loc": "center left", "bbox_to_anchor": (1.02, 0.5)}


def test_outside_top_uses_fixed_loc_and_bbox_anchor():
    result = resolve_legend_placement("outside_top", 1.02, 0.5, "center left")
    assert result == {"loc": "lower center", "bbox_to_anchor": (0.5, 1.02)}


def test_outside_bottom_uses_fixed_loc_and_bbox_anchor():
    result = resolve_legend_placement("outside_bottom", 1.02, 0.5, "center left")
    assert result == {"loc": "upper center", "bbox_to_anchor": (0.5, -0.08)}


def test_custom_uses_the_given_anchor_and_xy():
    result = resolve_legend_placement("custom", 0.3, 0.7, "upper left")
    assert result == {"loc": "upper left", "bbox_to_anchor": (0.3, 0.7)}
