"""Tests for SeriesConfigCard."""
import pytest
from PySide6.QtWidgets import QApplication

from pandaplot.gui.dialogs.chart.chart_role_spec import get_chart_role_spec
from pandaplot.gui.dialogs.chart.series_config_card import SeriesConfigCard


@pytest.fixture(scope="module", autouse=True)
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


def _line_card() -> SeriesConfigCard:
    card = SeriesConfigCard(role_spec=get_chart_role_spec("line"))
    card.set_datasets([("ds-1", "Sales")])
    card.set_dataset_columns("ds-1", [("col-date", "Date"), ("col-rev", "Revenue")])
    return card


def test_incomplete_until_required_role_is_filled():
    card = _line_card()
    assert card.is_complete() is False


def test_complete_once_y_role_is_selected():
    card = _line_card()
    card.y_column_combo.setCurrentIndex(card.y_column_combo.findData("col-rev"))

    assert card.is_complete() is True


def test_x_role_is_optional_for_line():
    card = _line_card()
    card.y_column_combo.setCurrentIndex(card.y_column_combo.findData("col-rev"))

    config = card.get_series_config()
    assert config["x_column_id"] == ""
    assert config["y_column_id"] == "col-rev"
    assert config["dataset_id"] == "ds-1"


def test_histogram_card_has_no_error_bar_toggle():
    card = SeriesConfigCard(role_spec=get_chart_role_spec("hist"))
    assert card.error_bars_check is None


def test_error_bars_hidden_until_toggled_on():
    card = _line_card()
    assert card.error_bars_check.isChecked() is False

    config = card.get_series_config()
    assert config["x_error_column_id"] == ""
    assert config["y_error_column_id"] == ""


def test_error_bars_columns_used_once_toggled_on():
    card = _line_card()
    card.error_bars_check.setChecked(True)
    card.y_error_column_combo.setCurrentIndex(card.y_error_column_combo.findData("col-rev"))

    config = card.get_series_config()
    assert config["y_error_column_id"] == "col-rev"
    assert config["error_symmetric"] is True


def test_apply_picked_columns_sets_the_named_role():
    card = _line_card()

    card.apply_picked_columns("y", ["col-rev"])

    assert card.y_column_combo.currentData() == "col-rev"


def test_apply_picked_columns_uses_only_the_first_id():
    card = _line_card()

    card.apply_picked_columns("y", ["col-rev", "col-date"])

    assert card.y_column_combo.currentData() == "col-rev"


def test_pick_button_emits_role_name(qapp):
    card = _line_card()
    received = []
    card.pickRequested.connect(received.append)

    card.y_pick_button.click()

    assert received == ["y"]


def test_remove_button_emits_remove_requested():
    card = _line_card()
    received = []
    card.removeRequested.connect(lambda: received.append(True))

    card.remove_button.click()

    assert received == [True]


def test_histogram_values_role_maps_to_y_column_id():
    card = SeriesConfigCard(role_spec=get_chart_role_spec("hist"))
    card.set_datasets([("ds-1", "Sales")])
    card.set_dataset_columns("ds-1", [("col-date", "Date"), ("col-rev", "Revenue")])
    card.values_column_combo.setCurrentIndex(card.values_column_combo.findData("col-rev"))

    config = card.get_series_config()

    assert config["y_column_id"] == "col-rev"
    assert "values_column_id" not in config


def test_switching_dataset_resets_column_selections():
    card = _line_card()
    card.y_column_combo.setCurrentIndex(card.y_column_combo.findData("col-rev"))
    assert card.y_column_combo.currentData() == "col-rev"

    card.set_datasets([("ds-1", "Sales"), ("ds-2", "Marketing")])
    card.dataset_combo.setCurrentIndex(card.dataset_combo.findData("ds-2"))
    card.set_dataset_columns("ds-2", [("col-cost", "Cost"), ("col-clicks", "Clicks")])

    assert card.dataset_combo.currentData() == "ds-2"
    assert card.y_column_combo.currentData() == ""
    assert card.x_column_combo.currentData() == ""
    assert [card.y_column_combo.itemData(i) for i in range(card.y_column_combo.count())] == [
        "",
        "col-cost",
        "col-clicks",
    ]


def test_display_names_empty_when_nothing_selected():
    card = _line_card()

    assert card.get_display_names() == {}


def test_display_names_includes_only_selected_roles():
    card = _line_card()
    card.y_column_combo.setCurrentIndex(card.y_column_combo.findData("col-rev"))

    assert card.get_display_names() == {"y": "Revenue"}


def test_display_names_uses_display_text_not_column_id():
    card = _line_card()
    card.x_column_combo.setCurrentIndex(card.x_column_combo.findData("col-date"))
    card.y_column_combo.setCurrentIndex(card.y_column_combo.findData("col-rev"))

    names = card.get_display_names()
    assert names == {"x": "Date", "y": "Revenue"}
    assert "col-date" not in names.values()
    assert "col-rev" not in names.values()


def test_display_names_for_histogram_uses_the_values_role():
    card = SeriesConfigCard(role_spec=get_chart_role_spec("hist"))
    card.set_datasets([("ds-1", "Sales")])
    card.set_dataset_columns("ds-1", [("col-rev", "Revenue")])
    card.values_column_combo.setCurrentIndex(card.values_column_combo.findData("col-rev"))

    assert card.get_display_names() == {"values": "Revenue"}


def test_display_names_never_includes_error_roles():
    card = _line_card()
    card.error_bars_check.setChecked(True)
    card.y_error_column_combo.setCurrentIndex(card.y_error_column_combo.findData("col-rev"))

    assert "y_error" not in card.get_display_names()
