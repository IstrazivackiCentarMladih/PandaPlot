"""Tests for ChartWizard."""
from unittest.mock import Mock

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from pandaplot.gui.dialogs.chart.chart_wizard import ChartWizard
from pandaplot.services.theme.theme_manager import ThemeManager


@pytest.fixture(scope="module", autouse=True)
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


_FAKE_PALETTE = {
    "card_bg": "#111111",
    "card_hover": "#222222",
    "card_pressed": "#333333",
    "card_border": "#444444",
    "base_fg": "#eeeeee",
    "secondary_fg": "#aaaaaa",
    "accent": "#ff00ff",
}


def _fake_app_context():
    app_context = Mock()
    app_context.event_bus = Mock()

    theme_manager = Mock()
    theme_manager.get_surface_palette.return_value = dict(_FAKE_PALETTE)

    def _get_manager(manager_type, *args, **kwargs):
        if manager_type is ThemeManager:
            return theme_manager
        return Mock()

    app_context.get_manager.side_effect = _get_manager
    return app_context


def _columns_for(dataset_id: str):
    return [("col-date", "Date"), ("col-rev", "Revenue")]


def _make_wizard(**kwargs) -> ChartWizard:
    return ChartWizard(
        app_context=_fake_app_context(),
        datasets=[("ds-1", "Sales")],
        columns_provider=_columns_for,
        **kwargs,
    )


def test_defaults_to_line_with_one_incomplete_series():
    wizard = _make_wizard()

    assert wizard.get_chart_type() == "line"
    assert wizard.is_empty() is False


def test_empty_requested_on_type_page_finishes_empty_with_line_type():
    wizard = _make_wizard()

    wizard.type_page.emptyRequested.emit()

    assert wizard.is_empty() is True
    assert wizard.get_chart_type() == "line"
    assert wizard.get_series_configs() == []


def test_empty_requested_on_data_page_finishes_empty_with_chosen_type():
    wizard = _make_wizard()
    histogram_row = next(
        row for row in range(wizard.type_page.type_list.count())
        if wizard.type_page.type_list.item(row).data(Qt.ItemDataRole.UserRole) == "hist"
    )
    wizard.type_page.type_list.setCurrentRow(histogram_row)

    wizard.data_page.emptyRequested.emit()

    assert wizard.is_empty() is True
    assert wizard.get_chart_type() == "hist"


def test_initial_dataset_and_columns_preselect_the_first_series():
    wizard = _make_wizard(initial_dataset_id="ds-1", initial_column_ids=["col-date", "col-rev"])

    wizard.next()  # real navigation from the Type page to the Data page

    configs = wizard.get_series_configs()
    assert configs[0]["dataset_id"] == "ds-1"
    assert configs[0]["x_column_id"] == "col-date"
    assert configs[0]["y_column_id"] == "col-rev"


def test_single_preselected_column_fills_y_only():
    wizard = _make_wizard(initial_dataset_id="ds-1", initial_column_ids=["col-rev"])

    wizard.next()

    configs = wizard.get_series_configs()
    assert configs[0]["x_column_id"] == ""
    assert configs[0]["y_column_id"] == "col-rev"


def test_preselection_survives_back_then_a_chart_type_change():
    """Regression: Back → change chart type → Next must keep the pre-selection.

    `ChartDataPage.set_chart_type` rebuilds every card when the type actually
    changes, so the fresh card used to default to the project's first dataset
    instead of the dataset the user actually came from.
    """
    wizard = _make_wizard(initial_dataset_id="ds-1", initial_column_ids=["col-date", "col-rev"])

    wizard.next()   # Type page -> Data page: pre-selection applied to card 1
    wizard.back()   # back to the Type page

    bar_row = next(
        row for row in range(wizard.type_page.type_list.count())
        if wizard.type_page.type_list.item(row).data(Qt.ItemDataRole.UserRole) == "bar"
    )
    wizard.type_page.type_list.setCurrentRow(bar_row)

    wizard.next()   # forward again: cards are rebuilt for the new type

    assert wizard.get_chart_type() == "bar"
    configs = wizard.get_series_configs()
    assert configs[0]["dataset_id"] == "ds-1"
    assert configs[0]["x_column_id"] == "col-date"
    assert configs[0]["y_column_id"] == "col-rev"


def test_revisiting_the_data_page_without_a_type_change_keeps_user_edits():
    """The pre-selection must not be re-applied over what the user configured."""
    wizard = _make_wizard(initial_dataset_id="ds-1", initial_column_ids=["col-date", "col-rev"])

    wizard.next()
    card = wizard.data_page.cards[0]
    card.apply_picked_columns("y", ["col-date"])  # user overrides Y by hand

    wizard.back()
    wizard.next()  # same chart type -> no rebuild -> no re-apply

    assert wizard.data_page.cards[0] is card
    assert wizard.get_series_configs()[0]["y_column_id"] == "col-date"


def test_wizard_picks_up_the_application_theme():
    wizard = _make_wizard()

    stylesheet = wizard.styleSheet()

    assert stylesheet.strip() != ""
    assert _FAKE_PALETTE["accent"] in stylesheet
    assert _FAKE_PALETTE["card_bg"] in stylesheet
