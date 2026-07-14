"""Tests for resolve_series_data (no Qt widgets involved)."""

import pandas as pd

from pandaplot.gui.components.tabs.chart.chart_editor import resolve_series_data
from pandaplot.models.project.items.chart import DataSeries
from pandaplot.models.project.items.dataset import Dataset
from pandaplot.models.project.project import Project


def _project_with_dataset():
    project = Project("P")
    dataset = Dataset(name="ds", data=pd.DataFrame({"a": [1, 2], "b": [3, 4]}))
    project.add_item(dataset)
    return project, dataset


def test_resolves_x_and_y_columns():
    project, dataset = _project_with_dataset()
    series = DataSeries(dataset_id=dataset.id, x_column="a", y_column="b")
    x, y, error = resolve_series_data(project, series)
    assert error is None
    assert list(x) == [1, 2]
    assert list(y) == [3, 4]


def test_empty_x_column_uses_dataframe_index():
    project, dataset = _project_with_dataset()
    series = DataSeries(dataset_id=dataset.id, x_column="", y_column="b")
    x, y, error = resolve_series_data(project, series)
    assert error is None
    assert list(x) == [0, 1]


def test_missing_dataset_returns_error():
    project, _ = _project_with_dataset()
    series = DataSeries(dataset_id="nope", x_column="a", y_column="b")
    x, y, error = resolve_series_data(project, series)
    assert x is None and y is None
    assert "nope" in error


def test_missing_column_returns_error_naming_the_column():
    project, dataset = _project_with_dataset()
    series = DataSeries(dataset_id=dataset.id, x_column="a", y_column="gone")
    x, y, error = resolve_series_data(project, series)
    assert x is None and y is None
    assert "gone" in error


def test_no_project_returns_error():
    series = DataSeries(dataset_id="ds", x_column="a", y_column="b")
    x, y, error = resolve_series_data(None, series)
    assert error is not None
