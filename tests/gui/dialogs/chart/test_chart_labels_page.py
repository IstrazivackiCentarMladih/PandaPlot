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
