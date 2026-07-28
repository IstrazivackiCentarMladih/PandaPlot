"""Unit tests for compute_axis_data_range(), the pure helper that computes
the (min, max) of all series data plotted against a given axis -- used to
populate the Axes tab's Range card in both Auto (disabled, for reference)
and the moment of switching into Manual (recompute-fresh)."""
import numpy as np
import pytest

from pandaplot.gui.components.tabs.chart.chart_editor import compute_axis_data_range
from pandaplot.models.project.items.chart import DataSeries, YAxis
from pandaplot.models.project.items.dataset import Dataset


class _FakeProject:
    def __init__(self, datasets):
        self._datasets = {d.id: d for d in datasets}

    def find_item(self, item_id):
        return self._datasets.get(item_id)


def _make_dataset(id_, x, y):
    import pandas as pd
    ds = Dataset(id=id_, name=id_)
    ds.data = pd.DataFrame({"x": x, "y": y})
    return ds


def test_computes_min_max_across_all_series_on_the_x_axis():
    ds = _make_dataset("ds1", x=[1, 5, 3], y=[10, 20, 30])
    project = _FakeProject([ds])
    series = [DataSeries(dataset_id="ds1", x_column="x", y_column="y")]
    assert compute_axis_data_range(project, series, "x") == (1.0, 5.0)


def test_computes_min_max_for_y_axis():
    ds = _make_dataset("ds1", x=[1, 2], y=[10, 20])
    project = _FakeProject([ds])
    series = [DataSeries(dataset_id="ds1", x_column="x", y_column="y")]
    assert compute_axis_data_range(project, series, "y") == (10.0, 20.0)


def test_y2_only_includes_secondary_axis_series():
    ds = _make_dataset("ds1", x=[1, 2], y=[10, 20])
    project = _FakeProject([ds])
    primary = DataSeries(dataset_id="ds1", x_column="x", y_column="y", y_axis=YAxis.PRIMARY)
    secondary = DataSeries(dataset_id="ds1", x_column="x", y_column="y", y_axis=YAxis.SECONDARY)
    secondary.y_column = "y"
    assert compute_axis_data_range(project, [primary, secondary], "y2") == (10.0, 20.0)
    assert compute_axis_data_range(project, [primary, secondary], "y") == (10.0, 20.0)


def test_returns_none_when_no_series_have_resolvable_data():
    project = _FakeProject([])
    series = [DataSeries(dataset_id="missing", x_column="x", y_column="y")]
    assert compute_axis_data_range(project, series, "x") is None


def test_returns_none_for_empty_series_list():
    project = _FakeProject([])
    assert compute_axis_data_range(project, [], "x") is None


def test_combines_min_max_across_multiple_series():
    ds1 = _make_dataset("ds1", x=[1, 2], y=[10, 20])
    ds2 = _make_dataset("ds2", x=[-5, 0], y=[100, 200])
    project = _FakeProject([ds1, ds2])
    series = [
        DataSeries(dataset_id="ds1", x_column="x", y_column="y"),
        DataSeries(dataset_id="ds2", x_column="x", y_column="y"),
    ]
    assert compute_axis_data_range(project, series, "x") == (-5.0, 2.0)
