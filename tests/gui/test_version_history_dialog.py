"""GUI unit tests for VersionHistoryDialog."""

import pytest
from PySide6.QtCore import Qt

from pandaplot.gui.dialogs.version_history_dialog import VersionHistoryDialog
from pandaplot.models.events.event_bus import EventBus
from pandaplot.models.project import Project
from pandaplot.models.project.items import Note
from pandaplot.models.state.app_context import AppContext
from pandaplot.models.state.app_state import AppState
from pandaplot.storage.version_manager import VersionManager


from unittest.mock import Mock

def _make_app_context(app_state, event_bus):
    ctx = Mock(spec=AppContext)
    ctx.get_app_state.return_value = app_state
    ctx.get_event_bus.return_value = event_bus
    ctx.get_manager.side_effect = lambda m_cls: getattr(app_state, "_version_manager", None)
    return ctx

def test_version_history_dialog_init(qapp):
    event_bus = EventBus()
    app_state = AppState(event_bus)
    app_context = _make_app_context(app_state, event_bus)

    project = Project(name="Test Project")
    app_state.load_project(project)

    vm = VersionManager()
    app_state._version_manager = vm
    vm.create_project_snapshot(project, label="Initial")

    dialog = VersionHistoryDialog(app_context)
    assert dialog.table.rowCount() == 1
    assert dialog.table.item(0, 1).text() == "Initial"


def test_version_history_dialog_item(qapp):
    event_bus = EventBus()
    app_state = AppState(event_bus)
    app_context = _make_app_context(app_state, event_bus)

    project = Project(name="Test Project")
    note = Note(name="Test Note")
    project.add_item(note)
    app_state.load_project(project)

    vm = VersionManager()
    app_state._version_manager = vm
    vm.create_item_snapshot(note, label="Note V1")

    dialog = VersionHistoryDialog(app_context, item_id=note.id)
    assert dialog.table.rowCount() == 1
    assert dialog.table.item(0, 1).text() == "Note V1"
