"""Tests pinning resolve_series_data/compute_axis_data_range's per-type
column requirements to SERIES_TYPE_SPECS instead of hardcoded string
comparisons, and the compute_axis_data_range missing-chart_type-argument
bug fix."""
import pandas as pd
import pytest

from pandaplot.gui.components.tabs.chart.chart_editor import (
    compute_axis_data_range,
    resolve_series_data,
)
from pandaplot.models.project.items.chart import DataSeries
from pandaplot.models.project.items.dataset import Dataset
from pandaplot.models.project.project import Project


@pytest.fixture
def project_with_series():
    project = Project(name="P")
    dataset = Dataset(id="ds-1", name="Data", data=pd.DataFrame({"x": [1, 2, 3], "y": [4, 5, 6]}))
    project.add_item(dataset)
    return project, dataset


def test_hist_does_not_require_x_column(project_with_series):
    project, dataset = project_with_series
    series = DataSeries(dataset_id="ds-1", x_column_id="", y_column_id=dataset.column_id("y"))

    data = resolve_series_data(project, series, "hist")

    assert data.error is None


def test_line_requires_resolvable_x_column_when_configured(project_with_series):
    project, dataset = project_with_series
    series = DataSeries(dataset_id="ds-1", x_column_id="", x_column="not_a_column",
                         y_column_id=dataset.column_id("y"))

    data = resolve_series_data(project, series, "line")

    assert data.error is not None


def test_compute_axis_data_range_passes_chart_type_through(project_with_series):
    """Regression test for the bug where compute_axis_data_range called
    resolve_series_data(project, series) with no chart_type, so a hist
    series' stale/unset x_column was always (incorrectly) required."""
    project, dataset = project_with_series
    series = DataSeries(dataset_id="ds-1", x_column_id="", y_column_id=dataset.column_id("y"))

    result = compute_axis_data_range(project, [series], "x", chart_type="hist")

    # A hist series has no x-column data to range over (it plots only
    # y_data as a distribution) -- with chart_type correctly threaded
    # through, no x-range is produced, rather than erroring on a missing
    # x column that was never meant to be required.
    assert result is None
