"""Pure-numpy tests for the colormap/heatmap geometry helpers, independent of
Qt/matplotlib (mirrors test_chart_editor_background_rendering.py's approach)."""
import numpy as np
import pytest

from pandaplot.gui.components.tabs.chart.chart_heatmap import (
    pivot_to_grid,
    resolve_color_limits,
)


def test_resolve_color_limits_auto_uses_data_range():
    assert resolve_color_limits([3.0, 1.0, 2.0], auto=True, vmin=0.0, vmax=0.0) == (1.0, 3.0)


def test_resolve_color_limits_auto_ignores_non_finite():
    vmin, vmax = resolve_color_limits([1.0, np.nan, 5.0, np.inf], auto=True, vmin=0.0, vmax=0.0)
    assert (vmin, vmax) == (1.0, 5.0)


def test_resolve_color_limits_auto_all_non_finite_returns_none():
    assert resolve_color_limits([np.nan, np.inf], auto=True, vmin=0.0, vmax=0.0) == (None, None)


def test_resolve_color_limits_manual_passthrough():
    assert resolve_color_limits([0.0, 100.0], auto=False, vmin=10.0, vmax=20.0) == (10.0, 20.0)


def test_resolve_color_limits_manual_degenerate_pair_is_nudged():
    # vmin >= vmax would collapse the map to one color; the pair is separated.
    vmin, vmax = resolve_color_limits([0.0], auto=False, vmin=5.0, vmax=5.0)
    assert vmin == 5.0 and vmax > vmin


def test_pivot_to_grid_regular_grid():
    # A full 2x2 grid: (x, y) -> z.
    xs, ys, grid = pivot_to_grid([0, 1, 0, 1], [0, 0, 1, 1], [10, 20, 30, 40])
    assert list(xs) == [0.0, 1.0]
    assert list(ys) == [0.0, 1.0]
    # grid[j, i] is z at (xs[i], ys[j]).
    np.testing.assert_array_equal(grid, [[10.0, 20.0], [30.0, 40.0]])


def test_pivot_to_grid_missing_cell_is_nan():
    # (1, 1) is absent -> that cell stays NaN.
    xs, ys, grid = pivot_to_grid([0, 1, 0], [0, 0, 1], [10, 20, 30])
    assert np.isnan(grid[1, 1])
    assert grid[0, 0] == 10.0
    assert grid[0, 1] == 20.0
    assert grid[1, 0] == 30.0


def test_pivot_to_grid_duplicate_last_wins():
    xs, ys, grid = pivot_to_grid([0, 0], [0, 0], [1, 99])
    assert grid.shape == (1, 1)
    assert grid[0, 0] == 99.0


def test_pivot_to_grid_empty_raises():
    with pytest.raises(ValueError):
        pivot_to_grid([], [], [])


# --- matplotlib API smoke tests: guard the exact calls the renderer makes ---

def test_colormap_scatter_produces_colorbar_mappable():
    from matplotlib.figure import Figure

    fig = Figure()
    axes = fig.add_subplot(111)
    z = [1.0, 2.0, 3.0]
    vmin, vmax = resolve_color_limits(z, auto=True, vmin=0.0, vmax=0.0)
    mappable = axes.scatter([0, 1, 2], [0, 1, 0], c=z, cmap="viridis", vmin=vmin, vmax=vmax)
    # A colorbar can be built from the returned mappable, as update_chart does.
    cbar = fig.colorbar(mappable, ax=axes)
    assert cbar is not None
    cbar.remove()


def test_heatmap_pcolormesh_produces_colorbar_mappable():
    from matplotlib.figure import Figure

    fig = Figure()
    axes = fig.add_subplot(111)
    xs, ys, grid = pivot_to_grid([0, 1, 0, 1], [0, 0, 1, 1], [10, 20, 30, 40])
    mappable = axes.pcolormesh(xs, ys, grid, cmap="viridis", shading="nearest")
    cbar = fig.colorbar(mappable, ax=axes)
    assert cbar is not None
    cbar.remove()
