"""Tests for WizardHeader."""
import pytest
from PySide6.QtWidgets import QApplication

from pandaplot.gui.dialogs.chart.wizard_header import WizardHeader


@pytest.fixture(scope="module", autouse=True)
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


def test_header_has_a_fixed_40px_height():
    header = WizardHeader()

    assert header.height() == 40
    assert header.minimumHeight() == 40
    assert header.maximumHeight() == 40


def test_close_button_click_emits_close_clicked():
    header = WizardHeader()
    received = []
    header.closeClicked.connect(lambda: received.append(True))

    header.close_button.click()

    assert received == [True]


def test_set_tokens_does_not_raise():
    header = WizardHeader()

    header.set_tokens({"accent": "#4A56C6", "text_muted": "#6B7280", "border_panel": "#E5E6EA"})
    header.set_tokens({})  # missing keys fall back to defaults
