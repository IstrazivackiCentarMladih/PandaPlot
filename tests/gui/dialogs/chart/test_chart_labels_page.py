"""Tests for ChartLabelsPage."""
from unittest.mock import Mock

import pytest
from PySide6.QtWidgets import QApplication

from pandaplot.gui.dialogs.chart.chart_labels_page import ChartLabelsPage


@pytest.fixture(scope="module", autouse=True)
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


def _fake_app_context():
    app_context = Mock()
    app_context.event_bus = Mock()
    return app_context


def test_fields_start_empty():
    page = ChartLabelsPage(app_context=_fake_app_context())

    assert page.get_title() == ""
    assert page.get_x_label() == ""
    assert page.get_y_label() == ""


def test_set_defaults_populates_all_three_fields():
    page = ChartLabelsPage(app_context=_fake_app_context())

    page.set_defaults("Chart from Sales", "Date", "Revenue")

    assert page.get_title() == "Chart from Sales"
    assert page.get_x_label() == "Date"
    assert page.get_y_label() == "Revenue"


def test_fields_stay_editable_after_defaults_are_set():
    page = ChartLabelsPage(app_context=_fake_app_context())
    page.set_defaults("Chart from Sales", "Date", "Revenue")

    page.title_edit.setText("My custom title")
    page.y_label_edit.clear()

    assert page.get_title() == "My custom title"
    assert page.get_y_label() == ""
    assert page.get_x_label() == "Date"


def test_set_defaults_overwrites_previous_defaults():
    """Re-seeding (e.g. after a chart-type change) replaces stale defaults."""
    page = ChartLabelsPage(app_context=_fake_app_context())
    page.set_defaults("Old title", "Old X", "Old Y")

    page.set_defaults("New title", "New X", "New Y")

    assert page.get_title() == "New title"
    assert page.get_x_label() == "New X"
    assert page.get_y_label() == "New Y"


def test_set_defaults_overwrites_an_untouched_field_even_on_a_second_call():
    """Seeding itself must not mark a field as touched (regression guard for
    the blockSignals wiring in set_defaults)."""
    page = ChartLabelsPage(app_context=_fake_app_context())
    page.set_defaults("Old title", "Old X", "Old Y")

    page.set_defaults("Newer title", "Newer X", "Newer Y")

    assert page.get_title() == "Newer title"
    assert page.get_x_label() == "Newer X"
    assert page.get_y_label() == "Newer Y"


def test_a_field_touched_by_the_user_is_never_overwritten_again():
    page = ChartLabelsPage(app_context=_fake_app_context())
    page.set_defaults("Old title", "Old X", "Old Y")

    page.x_label_edit.setText("user typed this")  # simulates a real user edit
    page.set_defaults("New title", "New X", "New Y")

    assert page.get_x_label() == "user typed this"
    assert page.get_title() == "New title"
    assert page.get_y_label() == "New Y"


def test_subtitle_starts_empty():
    page = ChartLabelsPage(app_context=_fake_app_context())

    assert page.get_subtitle() == ""


def test_subtitle_is_directly_editable():
    page = ChartLabelsPage(app_context=_fake_app_context())

    page.subtitle_edit.setText("A closer look")

    assert page.get_subtitle() == "A closer look"


def test_legend_and_grid_default_on():
    page = ChartLabelsPage(app_context=_fake_app_context())

    assert page.get_show_legend() is True
    assert page.get_show_grid() is True


def test_legend_and_grid_toggles_are_independent():
    page = ChartLabelsPage(app_context=_fake_app_context())

    page.show_legend_toggle.setChecked(False)

    assert page.get_show_legend() is False
    assert page.get_show_grid() is True


def test_page_exposes_a_step_rail_and_footer_with_no_empty_link():
    page = ChartLabelsPage(app_context=_fake_app_context())

    assert page.step_rail is not None
    assert page.footer is not None
    assert page.footer.empty_link is None  # step 3: no "Create empty plot" link
