"""Helpers for the color-mapped chart types ("colormap" scatter and gridded
"heatmap"): resolving the color scale limits and pivoting scattered (x, y, z)
triples into the regular 2-D grid ``Axes.pcolormesh()`` expects.

Kept separate from the chart editor widget so the numeric geometry can be
unit-tested without any Qt/matplotlib widget setup (mirrors chart_error_bars).
"""

from typing import Optional

import numpy as np


def resolve_color_limits(
    z_data, auto: bool, vmin: float, vmax: float
) -> tuple[Optional[float], Optional[float]]:
    """Resolve the (vmin, vmax) passed to a colormap normalization.

    When ``auto`` the colormap spans the data's own finite min..max, returned
    so callers can label the colorbar consistently (matplotlib would do the
    same autoscaling internally, but returning it here keeps the value
    available). ``(None, None)`` is returned instead when the data has no
    finite values to autoscale from, letting matplotlib fall back to its own
    default. When not ``auto`` the explicit ``vmin``/``vmax`` are used as-is;
    an inverted or degenerate pair (vmin >= vmax) is nudged so the two limits
    never coincide, which would otherwise collapse the whole map to one color.
    """
    if auto:
        values = np.asarray(z_data, dtype=float)
        values = values[np.isfinite(values)]
        if values.size == 0:
            return None, None
        return float(values.min()), float(values.max())
    if vmin >= vmax:
        return vmin, vmin + 1.0
    return vmin, vmax


def pivot_to_grid(x_data, y_data, z_data):
    """Pivot scattered ``(x, y, z)`` triples into a dense grid for pcolormesh.

    Returns ``(xs, ys, grid)`` where ``xs``/``ys`` are the sorted unique x/y
    coordinates and ``grid`` has shape ``(len(ys), len(xs))`` with
    ``grid[j, i]`` the z value at ``(xs[i], ys[j])``. Cells with no matching
    sample are left as ``NaN`` (drawn transparent by pcolormesh), so the same
    routine handles a fully-populated regular grid and a sparse/ragged one.
    When the same (x, y) pair appears more than once the last occurrence wins,
    matching how a plain dict-style pivot would resolve duplicates.

    Raises ``ValueError`` when there are no points to grid, so the caller can
    surface a "no data" state rather than drawing an empty axes.
    """
    x = np.asarray(x_data, dtype=float)
    y = np.asarray(y_data, dtype=float)
    z = np.asarray(z_data, dtype=float)
    if x.size == 0 or y.size == 0 or z.size == 0:
        raise ValueError("no data to grid")

    xs = np.unique(x)
    ys = np.unique(y)
    # Map each coordinate to its index in the sorted-unique axis via searchsorted
    # (exact matches, since xs/ys came from the data itself).
    xi = np.searchsorted(xs, x)
    yi = np.searchsorted(ys, y)
    grid = np.full((ys.size, xs.size), np.nan)
    grid[yi, xi] = z
    return xs, ys, grid
