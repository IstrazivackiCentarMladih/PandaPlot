"""Tests for resolve_series_data's vector-plot (u/v/magnitude) resolution."""
import numpy as np
import pandas as pd

from pandaplot.gui.components.tabs.chart.chart_editor import resolve_series_data
from pandaplot.models.chart.series_style.vector import VectorSeriesStyle
from pandaplot.models.chart.series_type import SeriesType
from pandaplot.models.project.items import Dataset
from pandaplot.models.project.items.chart import DataSeries
from pandaplot.models.project.project import Project


def _project_with_vector_dataset():
    project = Project(name="Vector Project")
    df = pd.DataFrame({
        "x": [0, 1, 2], "y": [0, 1, 2], "u": [1.0, 0.5, -1.0], "v": [0.0, 1.0, 0.5],
        "mag": [1.0, 1.1, 1.5],
    })
    dataset = Dataset(name="ds1", data=df)
    project.add_item(dataset)
    return project, dataset


def test_resolve_series_data_resolves_u_and_v_for_vector_chart_type():
    project, dataset = _project_with_vector_dataset()
    series = DataSeries(
        dataset_id=dataset.id,
        x_column_id=dataset.column_id("x"), y_column_id=dataset.column_id("y"),
        series_type=SeriesType.VECTOR,
        style=VectorSeriesStyle(u_column_id=dataset.column_id("u"), v_column_id=dataset.column_id("v")),
    )

    data = resolve_series_data(project, series, "vector")

    assert data.error is None
    np.testing.assert_array_equal(data.u_data, [1.0, 0.5, -1.0])
    np.testing.assert_array_equal(data.v_data, [0.0, 1.0, 0.5])
    assert data.magnitude_data is None


def test_resolve_series_data_resolves_optional_magnitude_column():
    project, dataset = _project_with_vector_dataset()
    series = DataSeries(
        dataset_id=dataset.id,
        x_column_id=dataset.column_id("x"), y_column_id=dataset.column_id("y"),
        series_type=SeriesType.VECTOR,
        style=VectorSeriesStyle(
            u_column_id=dataset.column_id("u"), v_column_id=dataset.column_id("v"),
            magnitude_column_id=dataset.column_id("mag"),
        ),
    )

    data = resolve_series_data(project, series, "vector")

    assert data.error is None
    np.testing.assert_array_equal(data.magnitude_data, [1.0, 1.1, 1.5])


def test_resolve_series_data_errors_when_u_column_missing():
    project, dataset = _project_with_vector_dataset()
    series = DataSeries(
        dataset_id=dataset.id,
        x_column_id=dataset.column_id("x"), y_column_id=dataset.column_id("y"),
        series_type=SeriesType.VECTOR,
        style=VectorSeriesStyle(u_column_id="", v_column_id=dataset.column_id("v")),
    )

    data = resolve_series_data(project, series, "vector")

    assert data.error is not None
    assert data.u_data is None


def test_resolve_series_data_never_populates_uv_for_non_vector_chart_types():
    project, dataset = _project_with_vector_dataset()
    series = DataSeries(dataset_id=dataset.id, x_column_id=dataset.column_id("x"),
                        y_column_id=dataset.column_id("y"))

    data = resolve_series_data(project, series, "line")

    assert data.error is None
    assert data.u_data is None
    assert data.v_data is None
    assert data.magnitude_data is None
