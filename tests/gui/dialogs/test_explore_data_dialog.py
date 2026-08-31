"""Tests for ExploreDataDialog: which branch it builds (dataset list vs.
import/create actions) and what each interaction does.
"""
from unittest.mock import Mock

import pandas as pd
import pytest
from PySide6.QtWidgets import QApplication, QDialog

from pandaplot.gui.dialogs.explore_data_dialog import ExploreDataDialog
from pandaplot.models.project.items import Dataset


@pytest.fixture(scope="module", autouse=True)
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


def _make_dialog(app_context, on_import_data=None, on_create_dataset=None):
    return ExploreDataDialog(
        app_context,
        on_import_data=on_import_data or Mock(),
        on_create_dataset=on_create_dataset or Mock(),
        parent=None,
    )


def _dataset(name="Sales", rows=3, cols=2):
    data = pd.DataFrame({f"c{i}": range(rows) for i in range(cols)})
    return Dataset(id=f"ds-{name}", name=name, data=data)


def test_get_datasets_empty_when_no_project_open():
    app_context = Mock()
    app_context.get_app_state.return_value.has_project = False

    dialog = _make_dialog(app_context)

    assert dialog._get_datasets() == []


def test_get_datasets_empty_when_project_has_no_datasets():
    app_context = Mock()
    app_context.get_app_state.return_value.has_project = True
    project = Mock()
    project.get_all_items.return_value = []
    app_context.get_app_state.return_value.current_project = project

    dialog = _make_dialog(app_context)

    assert dialog._get_datasets() == []


def test_get_datasets_filters_to_dataset_items_only():
    app_context = Mock()
    app_context.get_app_state.return_value.has_project = True
    ds1, ds2 = _dataset("A"), _dataset("B")
    non_dataset_item = Mock()
    project = Mock()
    project.get_all_items.return_value = [ds1, non_dataset_item, ds2]
    app_context.get_app_state.return_value.current_project = project

    dialog = _make_dialog(app_context)

    assert dialog._get_datasets() == [ds1, ds2]


def test_dialog_builds_empty_state_actions_when_no_datasets():
    app_context = Mock()
    app_context.get_app_state.return_value.has_project = False

    dialog = _make_dialog(app_context)

    assert hasattr(dialog, "import_btn")
    assert hasattr(dialog, "create_btn")


def test_dialog_builds_dataset_list_when_datasets_exist():
    app_context = Mock()
    app_context.get_app_state.return_value.has_project = True
    project = Mock()
    project.get_all_items.return_value = [_dataset("A")]
    app_context.get_app_state.return_value.current_project = project

    dialog = _make_dialog(app_context)

    assert not hasattr(dialog, "import_btn")
    assert not hasattr(dialog, "create_btn")


def test_open_dataset_emits_tab_open_requested_and_accepts():
    app_context = Mock()
    app_context.get_app_state.return_value.has_project = False
    dialog = _make_dialog(app_context)
    dataset = _dataset("Sales")

    dialog._open_dataset(dataset)

    from pandaplot.models.events.event_types import UIEvents
    event_bus = app_context.get_app_state.return_value.event_bus
    event_bus.emit.assert_called_once_with(
        UIEvents.TAB_OPEN_REQUESTED, {"item_id": "ds-Sales", "item_name": "Sales"}
    )
    assert dialog.result() == QDialog.DialogCode.Accepted


def test_handle_import_data_invokes_callback_and_accepts():
    app_context = Mock()
    app_context.get_app_state.return_value.has_project = False
    on_import_data = Mock()
    dialog = _make_dialog(app_context, on_import_data=on_import_data)

    dialog._handle_import_data()

    on_import_data.assert_called_once()
    assert dialog.result() == QDialog.DialogCode.Accepted


def test_handle_create_dataset_invokes_callback_and_accepts():
    app_context = Mock()
    app_context.get_app_state.return_value.has_project = False
    on_create_dataset = Mock()
    dialog = _make_dialog(app_context, on_create_dataset=on_create_dataset)

    dialog._handle_create_dataset()

    on_create_dataset.assert_called_once()
    assert dialog.result() == QDialog.DialogCode.Accepted
