"""Tests for DataSeries.has_error_data, used by the Style tab to decide
whether the Error Bars card has anything to style."""
from pandaplot.models.project.items.chart import DataSeries


def _series(**kwargs):
    return DataSeries(dataset_id="ds1", x_column="x", y_column="y", **kwargs)


def test_no_error_columns_means_no_error_data():
    assert not _series().has_error_data


def test_y_error_column_id_means_has_error_data():
    assert _series(y_error_column_id="col-id").has_error_data


def test_x_error_column_id_means_has_error_data():
    assert _series(x_error_column_id="col-id").has_error_data


def test_legacy_name_only_column_means_has_error_data():
    """Old projects loaded before stable column ids only populate the
    legacy name field, not the id field."""
    assert _series(y_error_column="err").has_error_data
