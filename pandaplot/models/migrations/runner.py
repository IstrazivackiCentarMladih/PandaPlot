"""Runs the registered cross-item migrations to bring a loaded Project
up to CURRENT_SCHEMA_VERSION.

Cross-item migrations need other items' data (e.g. a chart series
resolving its dataset's column ids) and so can only run after every item
has been loaded and attached to the project tree — unlike per-item
migrations (see migrations/per_item/), which are pure dict -> dict
transforms run before an item is even constructed.
"""
from pandaplot.models.migrations.cross_item.registry import CROSS_ITEM_MIGRATIONS
from pandaplot.models.migrations.schema_version import CURRENT_SCHEMA_VERSION
from pandaplot.models.project.project import Project


def run_cross_item_migrations(project: Project) -> None:
    while project.schema_version < CURRENT_SCHEMA_VERSION:
        migrate = CROSS_ITEM_MIGRATIONS.get(project.schema_version)
        if migrate is not None:
            migrate(project)
        project.schema_version += 1
