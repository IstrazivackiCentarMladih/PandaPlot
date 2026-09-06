"""Unit tests for versioning commands."""

import pytest
import pandas as pd

from pandaplot.commands.base_command import CommandResult
from pandaplot.commands.project.versioning.create_version_snapshot_command import CreateVersionSnapshotCommand
from pandaplot.commands.project.versioning.revert_to_version_command import RevertToVersionCommand
from pandaplot.models.events.event_bus import EventBus
from pandaplot.models.project import Project
from pandaplot.models.project.items import Note, Dataset
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

def test_create_and_revert_project_snapshot():
    event_bus = EventBus()
    app_state = AppState(event_bus)
    app_context = _make_app_context(app_state, event_bus)

    project = Project(name="Original Project")
    app_state.load_project(project)

    vm = VersionManager()
    app_state._version_manager = vm

    # Create project snapshot
    cmd = CreateVersionSnapshotCommand(app_context, label="V1")
    res = cmd.execute()
    assert res is CommandResult.SUCCESS
    assert cmd.created_version_id is not None

    # Modify project
    project.name = "Modified Project"
    assert app_state.current_project.name == "Modified Project"

    # Revert to snapshot
    revert_cmd = RevertToVersionCommand(app_context, version_id=cmd.created_version_id)
    res_revert = revert_cmd.execute()
    assert res_revert is CommandResult.SUCCESS
    assert app_state.current_project.name == "Original Project"


def test_create_and_revert_item_snapshot():
    event_bus = EventBus()
    app_state = AppState(event_bus)
    app_context = _make_app_context(app_state, event_bus)

    project = Project(name="Project")
    note = Note(name="Original Note", content="Original Content")
    project.add_item(note)
    app_state.load_project(project)

    vm = VersionManager()
    app_state._version_manager = vm

    # Create item snapshot
    cmd = CreateVersionSnapshotCommand(app_context, label="Note V1", item_id=note.id)
    res = cmd.execute()
    assert res is CommandResult.SUCCESS

    # Modify note
    note.content = "Modified Content"
    assert note.content == "Modified Content"

    # Revert item snapshot
    revert_cmd = RevertToVersionCommand(app_context, version_id=cmd.created_version_id)
    res_revert = revert_cmd.execute()
    assert res_revert is CommandResult.SUCCESS
    assert note.content == "Original Content"
