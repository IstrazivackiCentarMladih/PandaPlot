"""Helpers for turning a series' resolved error column(s) into the arrays
matplotlib's ``Axes.errorbar()`` expects.

Kept separate from the chart editor widget so the error-bar geometry can be
unit-tested without any Qt/matplotlib widget setup.
"""

import numpy as np

from pandaplot.models.chart.error_direction import ErrorDirection


def _symmetric_directional_error(magnitude, direction: ErrorDirection):
    """Turn a symmetric error magnitude into the array matplotlib expects.

    ErrorDirection.PLUS/MINUS produce an asymmetric (2, N) array with the
    unused side zeroed out, since matplotlib's errorbar() only accepts a
    single magnitude or an explicit lower/upper pair.
    """
    if magnitude is None:
        return None
    if direction == ErrorDirection.BOTH:
        return magnitude
    zeros = np.zeros_like(magnitude)
    return np.vstack([zeros, magnitude]) if direction == ErrorDirection.PLUS else np.vstack([magnitude, zeros])


def build_error_array(magnitude, minus_magnitude, direction, symmetric):
    """Combine a series' resolved error column(s) into what errorbar() expects.

    In symmetric mode only `magnitude` is used, expanded per `direction` via
    _symmetric_directional_error. In asymmetric mode `magnitude` is the
    upper (+) error and `minus_magnitude` the lower (-) error; either side
    missing is treated as zero so a one-sided uncertainty column is still
    usable on its own.
    """
    if symmetric:
        return _symmetric_directional_error(magnitude, direction)
    if magnitude is None and minus_magnitude is None:
        return None
    n = len(magnitude) if magnitude is not None else len(minus_magnitude)
    zeros = np.zeros(n)
    lower = minus_magnitude if minus_magnitude is not None else zeros
    upper = magnitude if magnitude is not None else zeros
    return np.vstack([lower, upper])
