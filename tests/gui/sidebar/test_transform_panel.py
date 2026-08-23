"""Smoke tests for TransformPanel construction.

TransformPanel moved its `apply_btn`/`clear_btn`/`preview_btn` `.clicked.connect(...)`
calls into the constructor via PButton's `on_click=` param. Nothing previously
constructed TransformPanel in tests, so a future construction-order regression would
go unnoticed. These tests just build the panel and check the buttons exist.
"""
from unittest.mock import Mock

import pytest
from PySide6.QtWidgets import QApplication

from pandaplot.gui.components.common.p_button import PButton
from pandaplot.gui.components.sidebar.transform.transform_panel import TransformPanel
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
def transform_panel(app_context):
    return TransformPanel(app_context)


def test_transform_panel_constructs_with_expected_buttons(transform_panel):
    assert isinstance(transform_panel.apply_btn, PButton)
    assert isinstance(transform_panel.clear_btn, PButton)
    assert isinstance(transform_panel.preview_btn, PButton)


def test_preview_button_click_invokes_update_preview(transform_panel):
    transform_panel.preview_text.setPlainText("stale")

    transform_panel.preview_btn.click()

    assert transform_panel.preview_text.toPlainText() == "No data available for preview"
