"""Tests for calculating confidence interval around fitted curve."""

import numpy as np

from pandaplot.services.fit.fit_service import FitService


def test_calculate_confidence_band_returns_bounds():
    """Calculate confidence interval around fitted curve."""

    service = FitService()

    def linear_func(x, a, b):
        return a * x + b

    x_data = np.array([0, 1, 2, 3, 4])
    x_fit = np.array([0, 1, 2, 3, 4])

    popt = np.array([2.0, 1.0])

    pcov = np.array([
        [0.04, 0.0],
        [0.0, 0.01] ])

    lower, upper = service._calculate_confidence_band(linear_func, x_fit, popt, pcov, x_data)

    assert lower is not None
    assert upper is not None

    assert len(lower) == len(x_fit)
    assert len(upper) == len(x_fit)

    np.testing.assert_array_less(lower, upper)