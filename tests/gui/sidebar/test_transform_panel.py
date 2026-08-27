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


def test_controller_transform_failed_surfaces_message_in_preview(transform_panel):
    transform_panel.on_controller_transform_failed(
        "dataset-1", "Column 'a_x2' already exists. Choose a different name or enable replace option."
    )

    assert transform_panel.preview_text.toPlainText() == (
        "Transform failed: Column 'a_x2' already exists. Choose a different name or enable replace option."
    )


def test_apply_transform_generic_failure_surfaces_message_when_no_signal_fired(transform_panel, app_context):
    transform_panel.current_dataset = Mock(id="dataset-1", data=Mock(columns=["a"]))
    transform_panel.source_column_list.addItem("a")
    transform_panel.source_column_list.item(0).setSelected(True)
    transform_panel.new_column_name.setText("b")
    transform_panel.function_text.setPlainText("x * 2")
    transform_panel.transform_controller.apply_transformation = Mock(return_value=False)

    transform_panel.apply_transform()

    assert transform_panel.preview_text.toPlainText() == "Transform failed - see logs for details"


def test_variable_hint_is_empty_before_any_column_is_selected(transform_panel):
    assert transform_panel.variable_hint_label.text() == ""


def test_variable_hint_names_the_selected_column_and_its_direct_usability(transform_panel):
    """Regression (#203): x always refers to the first selected column, but
    which one was easy to lose track of -- the hint spells it out, plus
    whether the column's own name doubles as an expression variable."""
    transform_panel.source_column_list.addItem("temp")
    transform_panel.source_column_list.item(0).setSelected(True)

    hint = transform_panel.variable_hint_label.text()
    assert '"temp"' in hint
    assert "usable directly as temp" in hint


def test_variable_hint_omits_direct_usage_note_for_a_non_identifier_column_name(transform_panel):
    """A column name with a space (or any other non-identifier name) can't
    be written directly into a Python expression, so the hint must not
    claim otherwise -- only the generic x/value/column/data aliases apply."""
    transform_panel.source_column_list.addItem("my col")
    transform_panel.source_column_list.item(0).setSelected(True)

    hint = transform_panel.variable_hint_label.text()
    assert '"my col"' in hint
    assert "usable directly" not in hint


def test_variable_hint_flags_extra_selected_columns_as_unused(transform_panel):
    """Only the first selected column is ever used (_execute_column_operation),
    so selecting more must not silently look like they all feed the
    expression."""
    transform_panel.source_column_list.addItem("a")
    transform_panel.source_column_list.addItem("b")
    transform_panel.source_column_list.item(0).setSelected(True)
    transform_panel.source_column_list.item(1).setSelected(True)

    hint = transform_panel.variable_hint_label.text()
    assert '"a"' in hint
    assert "no effect" in hint


def test_variable_hint_clears_when_selection_is_cleared(transform_panel):
    transform_panel.source_column_list.addItem("a")
    transform_panel.source_column_list.item(0).setSelected(True)
    assert transform_panel.variable_hint_label.text() != ""

    transform_panel.source_column_list.item(0).setSelected(False)

    assert transform_panel.variable_hint_label.text() == ""
