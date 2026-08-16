"""Tests for the cross-item migration runner.

The runner repeatedly looks up and applies the migration registered for
a project's current schema_version, bumping the version each time, until
the project reaches CURRENT_SCHEMA_VERSION. This pins down the loop
behavior independent of what any specific registered migration does.
"""
from unittest.mock import patch

from pandaplot.models.migrations.runner import run_cross_item_migrations
from pandaplot.models.project.project import Project


def test_runs_registered_migration_and_bumps_version():
    project = Project(name="P")
    project.schema_version = 0
    calls = []

    with patch(
        "pandaplot.models.migrations.runner.CROSS_ITEM_MIGRATIONS",
        {0: lambda p: calls.append(p)},
    ), patch("pandaplot.models.migrations.runner.CURRENT_SCHEMA_VERSION", 1):
        run_cross_item_migrations(project)

    assert calls == [project]
    assert project.schema_version == 1


def test_noop_when_already_current():
    project = Project(name="P")
    project.schema_version = 1
    calls = []

    with patch(
        "pandaplot.models.migrations.runner.CROSS_ITEM_MIGRATIONS",
        {0: lambda p: calls.append(p)},
    ), patch("pandaplot.models.migrations.runner.CURRENT_SCHEMA_VERSION", 1):
        run_cross_item_migrations(project)

    assert calls == []
    assert project.schema_version == 1


def test_chains_through_multiple_versions():
    project = Project(name="P")
    project.schema_version = 0
    calls = []

    with patch(
        "pandaplot.models.migrations.runner.CROSS_ITEM_MIGRATIONS",
        {0: lambda p: calls.append("0->1"), 1: lambda p: calls.append("1->2")},
    ), patch("pandaplot.models.migrations.runner.CURRENT_SCHEMA_VERSION", 2):
        run_cross_item_migrations(project)

    assert calls == ["0->1", "1->2"]
    assert project.schema_version == 2


def test_skips_a_version_with_no_registered_migration():
    project = Project(name="P")
    project.schema_version = 0
    calls = []

    with patch(
        "pandaplot.models.migrations.runner.CROSS_ITEM_MIGRATIONS",
        {1: lambda p: calls.append("1->2")},  # nothing registered for version 0
    ), patch("pandaplot.models.migrations.runner.CURRENT_SCHEMA_VERSION", 2):
        run_cross_item_migrations(project)

    assert calls == ["1->2"]
    assert project.schema_version == 2
