"""Tests for extracting sigma_y with asymmetric error bars."""
from unittest.mock import Mock

import numpy as np
import pandas as pd

from pandaplot.services.fit.fit_service import FitService

def test_extract_sigma_y_asymmetric():
    """Extract asymmetric y uncertainties as averaged magnitudes."""

    df = pd.DataFrame({
        "x": [0, 1, 2],
        "y": [1.0, 2.0, 3.0],
        "error_plus": [0.2, 0.4, 0.6],
        "error_minus": [0.1, 0.2, 0.3]})

    mask = np.array([True, True, True])

    series = Mock()
    series.y_error_column = "error_plus"
    series.y_error_minus_column = "error_minus"

    service = FitService(Mock())
    sigma = service._extract_sigma_y(df, mask, series)
    expected = np.array([0.15, 0.30, 0.45])

    np.testing.assert_allclose(sigma, expected)