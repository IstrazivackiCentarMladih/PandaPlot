"""Tests for extracting sigma_y with missing error bars returns none"""
from unittest.mock import Mock

import numpy as np
import pandas as pd

from pandaplot.services.fit.fit_service import FitService

def test_extract_sigma_y_missing_column_returns_none():
    """Return None when selected error column does not exist."""

    df = pd.DataFrame({
        "x": [0, 1, 2],
        "y": [1.0, 2.0, 3.0],
    })

    mask = np.array([True, True, True])

    series = Mock()
    series.y_error_column = "missing_error"
    series.y_error_minus_column = ""

    service = FitService(Mock())

    sigma = service._extract_sigma_y(df, mask, series)

    assert sigma is None