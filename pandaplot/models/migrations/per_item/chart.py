"""Per-item migrations for chart raw dicts.

Pure dict -> dict transforms, run before Chart.from_dict() constructs the
object — unlike cross-item migrations (see migrations/cross_item/),
these cannot look up another item's data (e.g. a dataset), only reshape
the chart's own dict. Empty as of Phase 1; Phase 3 registers the
DataSeries flat-fields -> series_type + typed style restructuring here.
"""
from typing import Callable

from pandaplot.models.migrations.schema_version import CURRENT_SCHEMA_VERSION

PER_ITEM_CHART_MIGRATIONS: dict[int, Callable[[dict], dict]] = {}


def migrate_chart(raw: dict, schema_version: int) -> dict:
    while schema_version < CURRENT_SCHEMA_VERSION:
        migrate = PER_ITEM_CHART_MIGRATIONS.get(schema_version)
        if migrate is None:
            break
        raw = migrate(raw)
        schema_version += 1
    return raw
