"""Tests for the Dataset column-id registry and its stability across edits."""

import numpy as np
import pandas as pd

from pandaplot.models.project.items.chart import (
    Chart,
    DataSeries,
    resolve_series_column,
)
from pandaplot.models.project.items.dataset import Dataset


def test_columns_get_ids_and_are_resolvable():
    ds = Dataset(name="ds", data=pd.DataFrame({"a": [1], "b": [2]}))
    assert set(ds.column_ids.values()) == {"a", "b"}
    a_id = ds.column_id("a")
    assert a_id is not None
    assert ds.column_name(a_id) == "a"
    assert ds.column_id("missing") is None


def test_rename_preserves_id():
    ds = Dataset(name="ds", data=pd.DataFrame({"a": [1], "b": [2]}))
    a_id = ds.column_id("a")

    returned = ds.rename_column("a", "time")
    ds.data.rename(columns={"a": "time"}, inplace=True)

    assert returned == a_id
    assert ds.column_id("time") == a_id  # id is stable across the rename
    assert ds.column_id("a") is None
    assert ds.column_name(a_id) == "time"


def test_set_data_syncs_ids_by_name():
    ds = Dataset(name="ds", data=pd.DataFrame({"a": [1], "b": [2]}))
    a_id = ds.column_id("a")

    # Add a column and drop another; matching names keep their ids.
    ds.set_data(pd.DataFrame({"a": [1], "c": [3]}))

    assert ds.column_id("a") == a_id  # preserved
    assert ds.column_name(a_id) == "a"
    assert ds.column_id("b") is None  # dropped
    assert ds.column_id("c") is not None  # freshly assigned


def test_rename_column_unknown_name_returns_none():
    ds = Dataset(name="ds", data=pd.DataFrame({"a": [1]}))
    assert ds.rename_column("nope", "x") is None


def test_serialization_round_trip_preserves_ids():
    ds = Dataset(name="ds", data=pd.DataFrame({"a": [1], "b": [2]}))
    a_id = ds.column_id("a")

    restored = Dataset.from_dict(ds.to_dict())
    # from_dict restores the registry even before the DataFrame is attached.
    assert restored.column_id("a") == a_id


def test_resolver_prefers_id_falls_back_to_name():
    ds = Dataset(name="ds", data=pd.DataFrame({"a": [1], "b": [2]}))
    a_id = ds.column_id("a")

    # id resolves to current name even if the stored fallback name is stale
    ds.rename_column("a", "time")
    ds.data.rename(columns={"a": "time"}, inplace=True)
    assert resolve_series_column(ds, a_id, "a") == "time"

    # empty id -> fall back to the stored name
    assert resolve_series_column(ds, "", "b") == "b"

    # neither resolves -> None
    assert resolve_series_column(ds, "", "") is None
    assert resolve_series_column(ds, "bogus-id", "gone") == "gone"


def test_assign_series_column_ids_via_dataset():
    from pandaplot.models.project.items.chart import assign_series_column_ids

    ds = Dataset(name="ds", data=pd.DataFrame({"a": [1], "b": [2]}))
    series = DataSeries(dataset_id=ds.id, x_column="a", y_column="b")
    assign_series_column_ids(series, ds)

    assert series.x_column_id == ds.column_id("a")
    assert series.y_column_id == ds.column_id("b")


def test_add_data_series_with_dataset_object_binds_ids():
    """Passing the Dataset object auto-binds column ids at the source."""
    ds = Dataset(name="ds", data=pd.DataFrame({"a": [1], "b": [2]}))
    chart = Chart(name="c")

    series = chart.add_data_series(ds, "a", "b", label="s")

    assert series.dataset_id == ds.id
    assert series.x_column_id == ds.column_id("a")
    assert series.y_column_id == ds.column_id("b")


def test_add_data_series_with_id_string_leaves_ids_empty():
    """Passing a bare id string (no dataset to resolve) yields name-only refs."""
    chart = Chart(name="c")
    series = chart.add_data_series("ds1", "x", "y")

    assert series.dataset_id == "ds1"
    assert series.x_column_id == ""
    assert series.y_column_id == ""


def test_add_fit_data_with_dataset_object_binds_ids():
    ds = Dataset(name="ds", data=pd.DataFrame({"a": [1], "b": [2]}))
    chart = Chart(name="c")

    fit = chart.add_fit_data(ds, "a", "b", "Linear",
                             np.array([1.0]), np.array([2.0]))

    assert fit.source_dataset_id == ds.id
    assert fit.source_x_column_id == ds.column_id("a")
    assert fit.source_y_column_id == ds.column_id("b")
