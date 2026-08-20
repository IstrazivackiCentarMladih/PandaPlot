"""Tests for extracting sigma_y with symmetric error bars."""

import numpy as np
import pandas as pd

from pandaplot.models.chart.error_bar_config import ErrorBarConfig
from pandaplot.models.chart.series_style.line import LineSeriesStyle
from pandaplot.models.project import Project
from pandaplot.models.project.items import Dataset
from pandaplot.models.project.items.chart import DataSeries
from pandaplot.services.fit.fit_service import FitService


def test_extract_sigma_y_symmetric():
    """Extract symmetric y uncertainties (error column referenced by id)."""

    df = pd.DataFrame({
        "x": [0, 1, 2],
        "y": [1.0, 2.0, 3.0],
        "std": [0.1, 0.2, 0.3]})

    dataset = Dataset(name="ds", data=df)
    project = Project("P")
    project.add_item(dataset)

    mask = np.array([True, True, True])

    series = DataSeries(
        dataset_id=dataset.id,
        style=LineSeriesStyle(error_bars=ErrorBarConfig(
            y_error_column_id=dataset.column_id("std"),
        )),
    )

    service = FitService()

    sigma = service._extract_sigma_y(dataset.data, mask, series, dataset=dataset)

    np.testing.assert_allclose(
        sigma,
        np.array([0.1, 0.2, 0.3]),
    )
