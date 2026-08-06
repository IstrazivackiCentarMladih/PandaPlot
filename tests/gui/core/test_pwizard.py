"""Tests for the PWizard/PWizardPage themed base classes."""
from unittest.mock import Mock

import pytest
from PySide6.QtWidgets import QApplication

from pandaplot.gui.core.widget_extension import PWizard, PWizardPage


@pytest.fixture(scope="module", autouse=True)
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


class _FakeApplyThemeWizard(PWizard):
    def _init_ui(self):
        self.applied_theme = False

    def _apply_theme(self):
        self.applied_theme = True


class _FakeApplyThemePage(PWizardPage):
    def _init_ui(self):
        self.applied_theme = False

    def _apply_theme(self):
        self.applied_theme = True


def _fake_app_context():
    app_context = Mock()
    app_context.event_bus = Mock()
    return app_context


def test_pwizard_runs_init_ui_and_apply_theme_via_initialize():
    wizard = _FakeApplyThemeWizard(app_context=_fake_app_context())
    wizard._initialize()

    assert wizard.applied_theme is True


def test_pwizardpage_runs_init_ui_and_apply_theme_via_initialize():
    page = _FakeApplyThemePage(app_context=_fake_app_context())
    page._initialize()

    assert page.applied_theme is True
