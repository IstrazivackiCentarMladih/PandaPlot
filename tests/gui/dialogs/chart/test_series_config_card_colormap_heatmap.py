"""Tests for SeriesConfigCard with the colormap/heatmap chart types' role spec."""
import sys

import pytest
from PySide6.QtWidgets import QApplication

from pandaplot.gui.dialogs.chart.series_config_card import SeriesConfigCard
from pandaplot.models.chart.chart_type_spec import get_chart_type_spec


@pytest.fixture(scope="module", autouse=True)
def qapp():
    yield QApplication.instance() or QApplication(sys.argv)


@pytest.mark.parametrize("chart_type", ["colormap", "heatmap"])
def test_card_exposes_z_column_combo(chart_type):
    card = SeriesConfigCard(role_spec=get_chart_type_spec(chart_type))
    assert hasattr(card, "z_column_combo")


@pytest.mark.parametrize("chart_type", ["colormap", "heatmap"])
def test_card_series_config_has_z_column_id_key(chart_type):
    card = SeriesConfigCard(role_spec=get_chart_type_spec(chart_type))
    card.set_datasets([("ds-1", "Dataset 1")])
    card.set_dataset_columns("ds-1", [("col-x", "X"), ("col-y", "Y"), ("col-z", "Z")])

    card.z_column_combo.setCurrentIndex(card.z_column_combo.findData("col-z"))

    config = card.get_series_config()
    assert config["z_column_id"] == "col-z"


@pytest.mark.parametrize("chart_type", ["colormap", "heatmap"])
def test_card_is_complete_requires_x_y_and_z(chart_type):
    card = SeriesConfigCard(role_spec=get_chart_type_spec(chart_type))
    card.set_datasets([("ds-1", "Dataset 1")])
    card.dataset_combo.setCurrentIndex(0)
    card.set_dataset_columns("ds-1", [("col-x", "X"), ("col-y", "Y"), ("col-z", "Z")])

    assert card.is_complete() is False

    card.x_column_combo.setCurrentIndex(card.x_column_combo.findData("col-x"))
    card.y_column_combo.setCurrentIndex(card.y_column_combo.findData("col-y"))
    assert card.is_complete() is False

    card.z_column_combo.setCurrentIndex(card.z_column_combo.findData("col-z"))
    assert card.is_complete() is True
