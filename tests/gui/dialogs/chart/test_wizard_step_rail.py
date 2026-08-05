"""Tests for WizardStepRail."""
import pytest
from PySide6.QtWidgets import QApplication

from pandaplot.gui.dialogs.chart.wizard_step_rail import WizardStepRail


@pytest.fixture(scope="module", autouse=True)
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


def test_current_step_label_is_bold_and_not_clickable():
    rail = WizardStepRail(["Type", "Data", "Labels"])
    rail.set_state(current_index=0, summaries={})

    received = []
    rail.stepClicked.connect(received.append)
    rail._step_widgets[0].click()

    assert received == []


def test_completed_step_is_clickable_and_shows_its_summary():
    rail = WizardStepRail(["Type", "Data", "Labels"])
    rail.set_state(current_index=2, summaries={0: "Type · Line", 1: "Data · 2 series"})

    assert rail._step_widgets[0].text() == "Type · Line"
    received = []
    rail.stepClicked.connect(received.append)
    rail._step_widgets[0].click()

    assert received == [0]


def test_upcoming_step_is_not_clickable():
    rail = WizardStepRail(["Type", "Data", "Labels"])
    rail.set_state(current_index=0, summaries={})

    received = []
    rail.stepClicked.connect(received.append)
    rail._step_widgets[2].click()

    assert received == []


def test_set_state_replaces_previous_summaries():
    rail = WizardStepRail(["Type", "Data", "Labels"])
    rail.set_state(current_index=1, summaries={0: "Type · Line"})

    rail.set_state(current_index=2, summaries={0: "Type · Bar", 1: "Data · 1 series"})

    assert rail._step_widgets[0].text() == "Type · Bar"
    assert rail._step_widgets[1].text() == "Data · 1 series"
