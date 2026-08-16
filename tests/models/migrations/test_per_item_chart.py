"""Tests for the per-item chart migration dispatcher.

The registry is empty as of Phase 1 (no chart-shape migration exists
yet — that lands in Phase 3), so these tests pin down the dispatcher's
loop behavior in isolation, the same way test_runner.py does for the
cross-item runner.
"""
from unittest.mock import patch

from pandaplot.models.migrations.per_item.chart import migrate_chart


def test_noop_when_registry_is_empty():
    raw = {"chart_type": "line"}

    result = migrate_chart(raw, schema_version=1)

    assert result == {"chart_type": "line"}


def test_applies_registered_migrations_in_order():
    calls = []

    def step_a(raw):
        calls.append("a")
        return {**raw, "a": True}

    def step_b(raw):
        calls.append("b")
        return {**raw, "b": True}

    with patch(
        "pandaplot.models.migrations.per_item.chart.PER_ITEM_CHART_MIGRATIONS",
        {0: step_a, 1: step_b},
    ), patch("pandaplot.models.migrations.per_item.chart.CURRENT_SCHEMA_VERSION", 2):
        result = migrate_chart({}, schema_version=0)

    assert calls == ["a", "b"]
    assert result == {"a": True, "b": True}


def test_starts_from_the_given_schema_version_not_zero():
    calls = []

    def step_a(raw):
        calls.append("a")
        return raw

    def step_b(raw):
        calls.append("b")
        return raw

    with patch(
        "pandaplot.models.migrations.per_item.chart.PER_ITEM_CHART_MIGRATIONS",
        {0: step_a, 1: step_b},
    ), patch("pandaplot.models.migrations.per_item.chart.CURRENT_SCHEMA_VERSION", 2):
        migrate_chart({}, schema_version=1)

    assert calls == ["b"]


def test_skips_a_version_with_no_registered_migration():
    calls = []

    def step_b(raw):
        calls.append("b")
        return {**raw, "b": True}

    with patch(
        "pandaplot.models.migrations.per_item.chart.PER_ITEM_CHART_MIGRATIONS",
        {1: step_b},  # nothing registered for version 0
    ), patch("pandaplot.models.migrations.per_item.chart.CURRENT_SCHEMA_VERSION", 2):
        result = migrate_chart({}, schema_version=0)

    assert calls == ["b"]
    assert result == {"b": True}
