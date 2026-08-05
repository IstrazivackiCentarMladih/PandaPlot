"""Tests for ChartWizard."""
from unittest.mock import Mock

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QWizard

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
    theme_manager.get_design_tokens.return_value = {
        "text_primary": "#1C1E26", "text_secondary": "#3F4350",
        "text_muted": "#6B7280", "text_hint": "#9AA0AB",
        "border_panel": "#E5E6EA", "border_control": "#DCDEE4",
        "border_subtle": "#ECEEF2",
        "surface_white": "#FFFFFF", "surface_chrome": "#FBFBFC",
        "surface_inset": "#F4F5F8",
        "accent": "#4A56C6", "accent_active_text": "#4A56C6",
        "accent_selected_bg": "#EEF0FB", "accent_disabled": "#AAB1E3",
        "status_modified_dot": "#E09A1F", "status_modified_text": "#B06A00",
        "status_success": "#3FA46A",
        "y2_accent": "#8A4BB8", "y2_accent_bg": "#F5EEFB",
        "series_palette": ["#A01818", "#4A56C6", "#2B7A8C", "#3FA46A", "#E09A1F"],
        "radius_swatch": 4, "radius_control": 5, "radius_card": 6, "radius_chip": 12,
    }

    def _get_manager(manager_type, *args, **kwargs):
        if manager_type is ThemeManager:
            return theme_manager
        return Mock()

    app_context.get_manager.side_effect = _get_manager
    return app_context


def _columns_for(dataset_id: str):
    return [("col-date", "Date"), ("col-rev", "Revenue"), ("col-cost", "Cost")]


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


def test_labels_default_to_blank_with_no_series():
    wizard = _make_wizard()
    wizard.next()  # Type -> Data
    wizard.next()  # Data -> Labels (default line card has no columns picked yet)

    assert wizard.get_x_label() == ""
    assert wizard.get_y_label() == ""


def test_labels_seeded_from_the_initial_title_and_first_series_columns():
    wizard = _make_wizard(initial_title="Chart from Sales", initial_dataset_id="ds-1",
                           initial_column_ids=["col-date", "col-rev"])
    wizard.next()  # Type -> Data: pre-selection applies Date/Revenue to card 1
    wizard.next()  # Data -> Labels

    assert wizard.get_title() == "Chart from Sales"
    assert wizard.get_x_label() == "Date"
    assert wizard.get_y_label() == "Revenue"


def test_histogram_seeds_x_label_only_never_y():
    wizard = _make_wizard(initial_title="Chart from Sales", initial_dataset_id="ds-1",
                           initial_column_ids=["col-rev"])
    histogram_row = next(
        row for row in range(wizard.type_page.type_list.count())
        if wizard.type_page.type_list.item(row).data(Qt.ItemDataRole.UserRole) == "hist"
    )
    wizard.type_page.type_list.setCurrentRow(histogram_row)
    wizard.next()  # Type -> Data: pre-selection fills the Values column
    wizard.next()  # Data -> Labels

    assert wizard.get_x_label() == "Revenue"
    assert wizard.get_y_label() == ""


def test_editing_labels_then_revisiting_without_a_rebuild_keeps_the_edit():
    wizard = _make_wizard(initial_title="Chart from Sales", initial_dataset_id="ds-1",
                           initial_column_ids=["col-date", "col-rev"])
    wizard.next()
    wizard.next()
    wizard.labels_page.title_edit.setText("My custom title")

    wizard.back()  # Labels -> Data
    wizard.next()  # Data -> Labels again, same chart type: no rebuild, no reseed

    assert wizard.get_title() == "My custom title"


def test_a_touched_axis_label_survives_a_chart_type_change():
    wizard = _make_wizard(initial_title="Chart from Sales", initial_dataset_id="ds-1",
                           initial_column_ids=["col-date", "col-rev"])
    wizard.next()
    wizard.next()
    wizard.labels_page.x_label_edit.setText("something the user typed")

    wizard.back()  # Labels -> Data
    wizard.back()  # Data -> Type
    bar_row = next(
        row for row in range(wizard.type_page.type_list.count())
        if wizard.type_page.type_list.item(row).data(Qt.ItemDataRole.UserRole) == "bar"
    )
    wizard.type_page.type_list.setCurrentRow(bar_row)
    wizard.next()  # Type -> Data: cards rebuilt for "bar"
    wizard.next()  # Data -> Labels: fresh cards, but the field was touched

    assert wizard.get_x_label() == "something the user typed"


def test_an_untouched_axis_label_still_updates_after_a_chart_type_change():
    wizard = _make_wizard(initial_title="Chart from Sales", initial_dataset_id="ds-1",
                           initial_column_ids=["col-date", "col-rev"])
    wizard.next()
    wizard.next()  # Data -> Labels: x label seeded to "Date", never touched

    wizard.back()  # Labels -> Data
    wizard.back()  # Data -> Type
    bar_row = next(
        row for row in range(wizard.type_page.type_list.count())
        if wizard.type_page.type_list.item(row).data(Qt.ItemDataRole.UserRole) == "bar"
    )
    wizard.type_page.type_list.setCurrentRow(bar_row)
    wizard.next()  # Type -> Data: cards rebuilt for "bar"
    wizard.next()  # Data -> Labels: untouched field refreshes to the new default

    assert wizard.get_x_label() == "Date"  # still derives correctly for the new type


def test_touched_title_survives_a_chart_type_change():
    wizard = _make_wizard(initial_title="Chart from Sales", initial_dataset_id="ds-1",
                           initial_column_ids=["col-date", "col-rev"])
    wizard.next()
    wizard.next()
    wizard.labels_page.title_edit.setText("My custom title")

    wizard.back()  # Labels -> Data
    wizard.back()  # Data -> Type
    bar_row = next(
        row for row in range(wizard.type_page.type_list.count())
        if wizard.type_page.type_list.item(row).data(Qt.ItemDataRole.UserRole) == "bar"
    )
    wizard.type_page.type_list.setCurrentRow(bar_row)
    wizard.next()  # Type -> Data: cards rebuilt for "bar"
    wizard.next()  # Data -> Labels: fresh cards, but the title was touched

    assert wizard.get_title() == "My custom title"


def test_untouched_label_updates_after_changing_the_picked_column_without_a_type_change():
    wizard = _make_wizard(initial_title="Chart from Sales", initial_dataset_id="ds-1",
                           initial_column_ids=["col-date", "col-rev"])
    wizard.next()
    wizard.next()  # Data -> Labels: y label seeded from Revenue, never touched

    assert wizard.get_y_label() == "Revenue"

    wizard.back()  # Labels -> Data
    card = wizard.data_page.cards[0]
    card.apply_picked_columns("y", ["col-cost"])  # user picks a different Y column

    wizard.next()  # Data -> Labels: same chart type, no rebuild, but untouched field refreshes

    assert wizard.get_y_label() == "Cost"


def test_get_labels_return_blank_on_the_empty_path():
    wizard = _make_wizard(initial_title="Chart from Sales", initial_dataset_id="ds-1",
                           initial_column_ids=["col-date", "col-rev"])
    wizard.type_page.emptyRequested.emit()

    assert wizard.get_title() == ""
    assert wizard.get_x_label() == ""
    assert wizard.get_y_label() == ""


def test_wizard_has_no_native_buttons_and_a_fixed_size():
    # Note: QWizard.buttonLayout() (the getter) isn't bound in this PySide6
    # version (only setButtonLayout() is) so the native-buttons assertion is
    # expressed behaviorally instead: after setButtonLayout([]), none of the
    # standard wizard buttons become visible once the wizard is shown.
    wizard = _make_wizard()

    assert wizard.size().toTuple() == (620, 440)

    wizard.show()
    for role in (
        QWizard.WizardButton.BackButton,
        QWizard.WizardButton.NextButton,
        QWizard.WizardButton.FinishButton,
        QWizard.WizardButton.CancelButton,
    ):
        assert not wizard.button(role).isVisible()


def test_generic_buttons_are_no_longer_forced_indigo():
    """Regression guard: the old global `QPushButton { background: accent }`
    rule made every button (including Back/Cancel) indigo. Per-page footers
    (added in later tasks) style Back/Cancel neutrally themselves; this test
    only guards that ChartWizard itself stops overriding button colors
    wholesale."""
    wizard = _make_wizard()

    assert "QPushButton {" not in wizard.styleSheet()
