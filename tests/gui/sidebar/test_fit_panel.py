"""Smoke tests for FitPanel construction.

FitPanel moved its `apply_button`/`fit_button`/`clear_button` `.clicked.connect(...)`
calls into the constructor via PButton's `on_click=`/`enabled=` params. That made
construction order matter: `fit_button` is built with `enabled=self.scipy_available`,
which requires `self.scipy_available` to already be assigned before
`_create_action_buttons` runs. Nothing previously constructed FitPanel in tests, so a
future construction-order regression (e.g. reordering the scipy check after UI setup)
would go unnoticed. These tests just build the panel and check the buttons exist.
"""
from unittest.mock import Mock

import pytest
from PySide6.QtWidgets import QApplication

from pandaplot.gui.components.common.p_button import PButton
from pandaplot.gui.components.sidebar.fit.fit_panel import FitPanel
from pandaplot.models.state.app_context import AppContext


@pytest.fixture(scope="module", autouse=True)
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


@pytest.fixture
def app_context():
    ctx = Mock(spec=AppContext)
    ctx.event_bus = Mock()
    return ctx


@pytest.fixture
def fit_panel(app_context):
    return FitPanel(app_context)


def test_fit_panel_constructs_with_expected_buttons(fit_panel):
    assert isinstance(fit_panel.fit_button, PButton)
    assert isinstance(fit_panel.apply_button, PButton)
    assert isinstance(fit_panel.clear_button, PButton)


def test_fit_button_enabled_state_matches_scipy_availability(fit_panel):
    # Directly covers the construction-order-sensitive `enabled=self.scipy_available`
    # retrofit: fit_button's enabled state must reflect scipy_available as computed
    # at construction time, not some later/default value.
    assert fit_panel.fit_button.isEnabled() == fit_panel.scipy_available


def test_apply_button_starts_disabled(fit_panel):
    assert fit_panel.apply_button.isEnabled() is False


def test_clear_button_click_invokes_clear_results(app_context):
    panel = FitPanel(app_context)
    panel.results_text.setPlainText("some results")

    panel.clear_button.click()

    assert panel.results_text.toPlainText() == ""
