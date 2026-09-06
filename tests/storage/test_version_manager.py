"""Unit tests for VersionManager and VersionSnapshot."""

import pytest
import pandas as pd

from pandaplot.models.project import Project
from pandaplot.models.project.items import Dataset, Note
from pandaplot.models.versioning.version_snapshot import VersionSnapshot
from pandaplot.storage.version_manager import VersionManager


def test_version_snapshot_serialization():
    snapshot = VersionSnapshot(
        version_id="v1",
        version_type="project",
        created_at="2026-01-01T00:00:00",
        label="Test Snapshot",
        item_id=None,
        data={"key": "value"},
    )
    d = snapshot.to_dict()
    assert d["version_id"] == "v1"
    assert d["version_type"] == "project"

    restored = VersionSnapshot.from_dict(d)
    assert restored.version_id == "v1"
    assert restored.label == "Test Snapshot"
    assert restored.data == {"key": "value"}


def test_version_manager_project_snapshot():
    project = Project(name="Test Project")
    vm = VersionManager()

    s1 = vm.create_project_snapshot(project, label="Initial State")
    assert s1.version_type == "project"
    assert s1.label == "Initial State"

    snapshots = vm.get_snapshots_for_project()
    assert len(snapshots) == 1
    assert snapshots[0].version_id == s1.version_id

    fetched = vm.get_snapshot(s1.version_id)
    assert fetched is not None
    assert fetched.label == "Initial State"


def test_version_manager_item_snapshot():
    note = Note(name="My Note", content="Hello World")
    vm = VersionManager()

    s1 = vm.create_item_snapshot(note, label="Note V1")
    assert s1.version_type == "item"
    assert s1.item_id == note.id

    snapshots = vm.get_snapshots_for_item(note.id)
    assert len(snapshots) == 1
    assert snapshots[0].label == "Note V1"


def test_version_manager_dataset_snapshot():
    df = pd.DataFrame({"a": [1, 2, 3], "b": [4, 5, 6]})
    dataset = Dataset(name="My Dataset", data=df)
    vm = VersionManager()

    s1 = vm.create_item_snapshot(dataset, label="Dataset V1")
    assert s1.version_type == "item"
    assert "_df_dict" in s1.data
    assert s1.data["_df_dict"]["a"] == [1, 2, 3]
