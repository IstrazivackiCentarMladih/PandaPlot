"""Tests for PreprocessingEngine."""

import numpy as np
import pandas as pd
import pytest

from pandaplot.analysis import PreprocessingEngine, PreprocessingMethod


@pytest.fixture
def series():
    return pd.Series([1.0, 2.0, 3.0, 4.0, 5.0], name="x")


def test_center_removes_mean(series):
    result = PreprocessingEngine.center(series)
    assert result.method == PreprocessingMethod.CENTER
    assert result.source_column == "x"
    assert result.statistics["mean"] == pytest.approx(3.0)
    assert result.data.mean() == pytest.approx(0.0)
    # Spread is preserved.
    assert result.data.std(ddof=0) == pytest.approx(series.std(ddof=0))


def test_standardize_zero_mean_unit_std(series):
    result = PreprocessingEngine.standardize(series)
    assert result.data.mean() == pytest.approx(0.0)
    assert result.data.std(ddof=0) == pytest.approx(1.0)
    assert result.statistics["mean"] == pytest.approx(3.0)


def test_standardize_constant_column_does_not_divide_by_zero():
    const = pd.Series([5.0, 5.0, 5.0], name="c")
    result = PreprocessingEngine.standardize(const)
    assert result.metadata["constant_column"] is True
    assert (result.data == 0.0).all()
    assert np.isfinite(result.data).all()


def test_minmax_default_range(series):
    result = PreprocessingEngine.minmax(series)
    assert result.data.min() == pytest.approx(0.0)
    assert result.data.max() == pytest.approx(1.0)
    assert result.statistics["min"] == pytest.approx(1.0)
    assert result.statistics["max"] == pytest.approx(5.0)


def test_minmax_custom_range(series):
    result = PreprocessingEngine.minmax(series, range_min=-1.0, range_max=1.0)
    assert result.data.min() == pytest.approx(-1.0)
    assert result.data.max() == pytest.approx(1.0)


def test_minmax_invalid_range_raises(series):
    with pytest.raises(ValueError):
        PreprocessingEngine.minmax(series, range_min=1.0, range_max=1.0)


def test_minmax_constant_column():
    const = pd.Series([7.0, 7.0], name="c")
    result = PreprocessingEngine.minmax(const)
    assert (result.data == 0.0).all()


def test_robust_scale(series):
    result = PreprocessingEngine.robust(series)
    # Median of 1..5 is 3, so the centered median is zero.
    assert result.data.median() == pytest.approx(0.0)
    assert result.statistics["median"] == pytest.approx(3.0)
    assert result.statistics["iqr"] == pytest.approx(2.0)


def test_robust_resistant_to_outlier():
    data = pd.Series([1.0, 2.0, 3.0, 4.0, 1000.0], name="x")
    result = PreprocessingEngine.robust(data)
    # The outlier does not distort the median/IQR based center and scale.
    assert result.statistics["median"] == pytest.approx(3.0)


def test_maxabs_maps_into_unit_interval():
    data = pd.Series([-4.0, -2.0, 0.0, 2.0, 4.0], name="x")
    result = PreprocessingEngine.maxabs(data)
    assert result.data.abs().max() == pytest.approx(1.0)
    assert result.data.iloc[2] == pytest.approx(0.0)  # zero stays zero
    assert result.statistics["max_abs"] == pytest.approx(4.0)


def test_transform_dispatches_by_method(series):
    for method in PreprocessingMethod:
        result = PreprocessingEngine.transform(method, series)
        assert result.method == method
        assert len(result.data) == len(series)


def test_nan_values_are_preserved(series):
    with_nan = pd.Series([1.0, np.nan, 3.0, 4.0, 5.0], name="x")
    result = PreprocessingEngine.standardize(with_nan)
    assert result.data.isna().sum() == 1
    # The mean was fitted ignoring the NaN.
    assert result.statistics["mean"] == pytest.approx(with_nan.mean())


def test_non_numeric_column_raises():
    text = pd.Series(["a", "b", "c"], name="t")
    with pytest.raises(ValueError):
        PreprocessingEngine.center(text)


def test_result_name_uses_suffix(series):
    result = PreprocessingEngine.standardize(series)
    assert result.result_name() == "x_zscore"
