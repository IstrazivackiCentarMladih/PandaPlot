"""Tests for SeriesConfigCard with the vector chart type's role spec."""
import sys

import pytest
from PySide6.QtWidgets import QApplication

from pandaplot.gui.dialogs.chart.chart_role_spec import get_chart_role_spec
from pandaplot.gui.dialogs.chart.series_config_card import SeriesConfigCard


@pytest.fixture(scope="module", autouse=True)
def qapp():
    yield QApplication.instance() or QApplication(sys.argv)


def test_vector_card_exposes_u_v_magnitude_combos():
    card = SeriesConfigCard(role_spec=get_chart_role_spec("vector"))
    assert hasattr(card, "u_column_combo")
    assert hasattr(card, "v_column_combo")
    assert hasattr(card, "magnitude_column_combo")


def test_vector_card_series_config_has_u_v_magnitude_keys():
    card = SeriesConfigCard(role_spec=get_chart_role_spec("vector"))
    card.set_datasets([("ds-1", "Dataset 1")])
    card.set_dataset_columns("ds-1", [("col-u", "U"), ("col-v", "V"), ("col-m", "M")])

    card.u_column_combo.setCurrentIndex(card.u_column_combo.findData("col-u"))
    card.v_column_combo.setCurrentIndex(card.v_column_combo.findData("col-v"))
    card.magnitude_column_combo.setCurrentIndex(card.magnitude_column_combo.findData("col-m"))

    config = card.get_series_config()
    assert config["u_column_id"] == "col-u"
    assert config["v_column_id"] == "col-v"
    assert config["magnitude_column_id"] == "col-m"


def test_vector_card_is_complete_requires_u_and_v_not_magnitude():
    card = SeriesConfigCard(role_spec=get_chart_role_spec("vector"))
    card.set_datasets([("ds-1", "Dataset 1")])
    card.dataset_combo.setCurrentIndex(0)
    card.set_dataset_columns("ds-1", [("col-x", "X"), ("col-y", "Y"), ("col-u", "U"), ("col-v", "V")])

    assert card.is_complete() is False

    card.x_column_combo.setCurrentIndex(card.x_column_combo.findData("col-x"))
    card.y_column_combo.setCurrentIndex(card.y_column_combo.findData("col-y"))
    card.u_column_combo.setCurrentIndex(card.u_column_combo.findData("col-u"))
    card.v_column_combo.setCurrentIndex(card.v_column_combo.findData("col-v"))

    assert card.is_complete() is True
