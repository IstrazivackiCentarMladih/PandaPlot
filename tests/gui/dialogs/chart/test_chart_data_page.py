"""Tests for ChartDataPage."""
from unittest.mock import Mock

import pytest
from PySide6.QtWidgets import QApplication

from pandaplot.gui.dialogs.chart.chart_data_page import ChartDataPage


@pytest.fixture(scope="module", autouse=True)
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


def _fake_app_context():
    app_context = Mock()
    app_context.event_bus = Mock()
    return app_context


def _columns_for(dataset_id: str) -> list[tuple[str, str]]:
    return [("col-date", "Date"), ("col-rev", "Revenue")]


def _make_page() -> ChartDataPage:
    page = ChartDataPage(app_context=_fake_app_context())
    page.set_chart_type("line")
    page.set_datasets([("ds-1", "Sales")])
    page.set_dataset_columns_provider(_columns_for)
    return page


def test_starts_with_exactly_one_series_card():
    page = _make_page()

    assert len(page.cards) == 1


def test_add_series_button_appends_a_card():
    page = _make_page()

    page.add_series_button.click()

    assert len(page.cards) == 2


def test_removing_a_card_via_its_signal_shrinks_the_list():
    page = _make_page()
    page.add_series_button.click()
    first_card = page.cards[0]

    first_card.removeRequested.emit()

    assert len(page.cards) == 1
    assert first_card not in page.cards


def test_incomplete_until_the_only_cards_required_role_is_filled():
    page = _make_page()

    assert page.isComplete() is False

    page.cards[0].y_column_combo.setCurrentIndex(page.cards[0].y_column_combo.findData("col-rev"))

    assert page.isComplete() is True


def test_series_configs_returns_one_dict_per_card():
    page = _make_page()
    page.cards[0].y_column_combo.setCurrentIndex(page.cards[0].y_column_combo.findData("col-rev"))

    configs = page.series_configs()

    assert len(configs) == 1
    assert configs[0]["dataset_id"] == "ds-1"
    assert configs[0]["y_column_id"] == "col-rev"


def test_empty_button_emits_empty_requested():
    page = _make_page()
    received = []
    page.emptyRequested.connect(lambda: received.append(True))

    page.empty_button.click()

    assert received == [True]


def test_changing_chart_type_resets_to_a_single_card_of_the_new_type():
    page = _make_page()
    page.add_series_button.click()
    assert len(page.cards) == 2

    page.set_chart_type("hist")

    assert len(page.cards) == 1
    assert page.cards[0].error_bars_check is None


def test_pick_requested_starts_the_picker_with_the_cards_dataset_and_role():
    page = _make_page()
    page._picker.start = Mock()
    card = page.cards[0]

    card.pickRequested.emit("y")

    page._picker.start.assert_called_once()
    args, kwargs = page._picker.start.call_args
    assert args[0] is page.wizard()
    assert args[1] == "ds-1"
    assert args[2] == "y"
    assert "on_done" in kwargs


def test_on_done_callback_applies_picked_columns_to_the_originating_card():
    page = _make_page()
    page._picker.start = Mock()
    card = page.cards[0]

    card.pickRequested.emit("y")

    on_done = page._picker.start.call_args.kwargs["on_done"]
    on_done(["col-rev"])

    assert card.y_column_combo.currentData() == "col-rev"


def test_pick_requested_without_a_selected_dataset_does_not_start_the_picker():
    page = _make_page()
    page._picker.start = Mock()
    card = page.cards[0]
    card.dataset_combo.setCurrentIndex(-1)

    card.pickRequested.emit("y")

    page._picker.start.assert_not_called()
