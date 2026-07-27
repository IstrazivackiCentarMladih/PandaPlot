"""Tests for extracting sigma_y with symmetric error bars."""

from unittest.mock import Mock

import numpy as np
import pandas as pd

from pandaplot.services.fit.fit_service import FitService


def test_extract_sigma_y_symmetric():
    """Extract symmetric y uncertainties."""

    # Create a simple dataset
    df = pd.DataFrame({
        "x": [0, 1, 2],
        "y": [1.0, 2.0, 3.0],
        "std": [0.1, 0.2, 0.3]})

    # Select all rows
    mask = np.array([True, True, True])

    # Mock a data series with symmetric error bars
    series = Mock()
    series.y_error_column = "std"
    series.y_error_minus_column = ""

    # Create the service (fit_panel is not used in this method)
    service = FitService(Mock())

    sigma = service._extract_sigma_y(df, mask, series)

    np.testing.assert_allclose(
        sigma,
        np.array([0.1, 0.2, 0.3]),
    )