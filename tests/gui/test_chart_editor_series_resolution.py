"""Tests for resolve_series_data and build_error_array (no Qt widgets involved)."""

import numpy as np
import pandas as pd

from pandaplot.gui.components.tabs.chart.chart_editor import build_error_array, resolve_series_data
from pandaplot.models.project.items.chart import DataSeries, ErrorDirection
from pandaplot.models.project.items.dataset import Dataset
from pandaplot.models.project.project import Project


def _project_with_dataset():
    project = Project("P")
    dataset = Dataset(name="ds", data=pd.DataFrame({
        "a": [1, 2], "b": [3, 4], "err": [0.1, 0.2], "err_minus": [0.05, 0.15],
    }))
    project.add_item(dataset)
    return project, dataset


def test_resolves_x_and_y_columns():
    project, dataset = _project_with_dataset()
    series = DataSeries(dataset_id=dataset.id, x_column="a", y_column="b")
    x, y, x_err, y_err, x_err_minus, y_err_minus, error = resolve_series_data(project, series)
    assert error is None
    assert list(x) == [1, 2]
    assert list(y) == [3, 4]
    assert x_err is None
    assert y_err is None
    assert x_err_minus is None
    assert y_err_minus is None


def test_empty_x_column_uses_dataframe_index():
    project, dataset = _project_with_dataset()
    series = DataSeries(dataset_id=dataset.id, x_column="", y_column="b")
    x, y, x_err, y_err, x_err_minus, y_err_minus, error = resolve_series_data(project, series)
    assert error is None
    assert list(x) == [0, 1]


def test_missing_dataset_returns_error():
    project, _ = _project_with_dataset()
    series = DataSeries(dataset_id="nope", x_column="a", y_column="b")
    x, y, x_err, y_err, x_err_minus, y_err_minus, error = resolve_series_data(project, series)
    assert x is None and y is None
    assert "nope" in error


def test_missing_column_returns_error_naming_the_column():
    project, dataset = _project_with_dataset()
    series = DataSeries(dataset_id=dataset.id, x_column="a", y_column="gone")
    x, y, x_err, y_err, x_err_minus, y_err_minus, error = resolve_series_data(project, series)
    assert x is None and y is None
    assert "gone" in error


def test_no_project_returns_error():
    series = DataSeries(dataset_id="ds", x_column="a", y_column="b")
    x, y, x_err, y_err, x_err_minus, y_err_minus, error = resolve_series_data(None, series)
    assert error is not None


def test_histogram_ignores_stale_x_column():
    project, dataset = _project_with_dataset()
    series = DataSeries(dataset_id=dataset.id, x_column="gone", y_column="b")
    x, y, x_err, y_err, x_err_minus, y_err_minus, error = resolve_series_data(project, series, chart_type="hist")
    assert error is None
    assert list(y) == [3, 4]


def test_resolves_y_error_column():
    project, dataset = _project_with_dataset()
    series = DataSeries(dataset_id=dataset.id, x_column="a", y_column="b", y_error_column="err")
    x, y, x_err, y_err, x_err_minus, y_err_minus, error = resolve_series_data(project, series)
    assert error is None
    assert list(y_err) == [0.1, 0.2]
    assert x_err is None


def test_missing_error_column_is_lenient():
    """A stale/unset error-column reference must not turn the whole series into an error."""
    project, dataset = _project_with_dataset()
    series = DataSeries(dataset_id=dataset.id, x_column="a", y_column="b", y_error_column="gone")
    x, y, x_err, y_err, x_err_minus, y_err_minus, error = resolve_series_data(project, series)
    assert error is None
    assert list(y) == [3, 4]
    assert y_err is None


def test_resolves_asymmetric_minus_column():
    project, dataset = _project_with_dataset()
    series = DataSeries(
        dataset_id=dataset.id, x_column="a", y_column="b",
        y_error_column="err", y_error_minus_column="err_minus", error_symmetric=False,
    )
    x, y, x_err, y_err, x_err_minus, y_err_minus, error = resolve_series_data(project, series)
    assert error is None
    assert list(y_err) == [0.1, 0.2]
    assert list(y_err_minus) == [0.05, 0.15]


# --- build_error_array ---

def test_symmetric_both_direction_returns_raw_magnitude():
    magnitude = np.array([0.1, 0.2])
    result = build_error_array(magnitude, None, direction=ErrorDirection.BOTH, symmetric=True)
    assert list(result) == [0.1, 0.2]


def test_symmetric_plus_direction_zeroes_lower_side():
    magnitude = np.array([0.1, 0.2])
    result = build_error_array(magnitude, None, direction=ErrorDirection.PLUS, symmetric=True)
    assert list(result[0]) == [0.0, 0.0]
    assert list(result[1]) == [0.1, 0.2]


def test_symmetric_no_magnitude_returns_none():
    assert build_error_array(None, None, direction=ErrorDirection.BOTH, symmetric=True) is None


def test_asymmetric_combines_plus_and_minus_columns():
    plus = np.array([0.1, 0.2])
    minus = np.array([0.05, 0.15])
    result = build_error_array(plus, minus, direction=ErrorDirection.BOTH, symmetric=False)
    assert list(result[0]) == [0.05, 0.15]
    assert list(result[1]) == [0.1, 0.2]


def test_asymmetric_missing_minus_side_defaults_to_zero():
    plus = np.array([0.1, 0.2])
    result = build_error_array(plus, None, direction=ErrorDirection.BOTH, symmetric=False)
    assert list(result[0]) == [0.0, 0.0]
    assert list(result[1]) == [0.1, 0.2]


def test_asymmetric_missing_plus_side_defaults_to_zero():
    minus = np.array([0.05, 0.15])
    result = build_error_array(None, minus, direction=ErrorDirection.BOTH, symmetric=False)
    assert list(result[0]) == [0.05, 0.15]
    assert list(result[1]) == [0.0, 0.0]


def test_asymmetric_no_columns_returns_none():
    assert build_error_array(None, None, direction=ErrorDirection.BOTH, symmetric=False) is None
