"""Tests for the per-item chart migration dispatcher.

As of Phase 3a, PER_ITEM_CHART_MIGRATIONS has its first real entry
(migrate_chart_v1_to_v2, see TestMigrateChartV1ToV2 below), so the
dispatcher-loop tests below patch the registry to whatever shape each
scenario needs -- pinning down migrate_chart's loop behavior in
isolation from the real migration content, the same way test_runner.py
does for the cross-item runner.
"""
from unittest.mock import patch

from pandaplot.models.migrations.per_item.chart import migrate_chart
from pandaplot.models.migrations.per_item.chart import migrate_chart_v1_to_v2
from pandaplot.models.migrations.per_item.chart import migrate_chart_v2_to_v3


def test_noop_when_registry_is_empty():
    raw = {"chart_type": "line"}

    with patch(
        "pandaplot.models.migrations.per_item.chart.PER_ITEM_CHART_MIGRATIONS", {}
    ), patch("pandaplot.models.migrations.per_item.chart.CURRENT_SCHEMA_VERSION", 2):
        # schema_version=1 < CURRENT_SCHEMA_VERSION=2, so the dispatcher's
        # while loop genuinely runs at least once and exercises the
        # `.get(...) is not None` skip-on-empty path against the
        # patched-empty registry -- not a vacuous pass from the loop never
        # executing (which would happen if schema_version >= CURRENT_SCHEMA_VERSION).
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


class TestMigrateChartV1ToV2:
    """The real v1->v2 per-item migration: adds series_type + style keys
    to each series dict, derived from the chart's chart_type and that
    series' own existing flat fields, without removing any existing key
    (this sub-phase is additive -- old flat fields stay in place)."""

    def test_adds_series_type_from_chart_type(self):
        raw = {
            "chart_type": "bar",
            "data_series": [{"dataset_id": "ds1", "x_column": "x", "y_column": "y", "color": "#112233"}],
        }

        migrated = migrate_chart_v1_to_v2(raw)

        assert migrated["data_series"][0]["series_type"] == "bar"

    def test_extracts_line_style_fields_into_a_style_dict(self):
        raw = {
            "chart_type": "line",
            "data_series": [{
                "dataset_id": "ds1", "x_column": "x", "y_column": "y",
                "color": "#112233", "line_style": "dashed", "line_width": 3.0,
                "marker_style": "square", "marker_size": 5.0,
                "marker_color": "#445566", "marker_edge_color": "#000000", "marker_edge_width": 2.0,
                "fill_enabled": True, "fill_color": "#778899", "fill_alpha": 0.5,
                "fill_orientation": "horizontal", "fill_base": 1.0, "fill_to_index": 2,
            }],
        }

        migrated = migrate_chart_v1_to_v2(raw)

        style = migrated["data_series"][0]["style"]
        assert style == {
            "color": "#112233", "marker_color": "#445566",
            "marker_edge_color": "#000000", "marker_edge_width": 2.0,
            "line_style": "dashed", "marker_style": "square",
            "line_width": 3.0, "marker_size": 5.0,
            "fill_enabled": True, "fill_color": "#778899", "fill_alpha": 0.5,
            "fill_orientation": "horizontal", "fill_base": 1.0, "fill_to_index": 2,
        }

    def test_extracts_bar_style_fields_only(self):
        raw = {
            "chart_type": "bar",
            "data_series": [{
                "dataset_id": "ds1", "x_column": "x", "y_column": "y",
                "color": "#112233", "line_style": "dashed",  # line_style present but irrelevant to bar
            }],
        }

        migrated = migrate_chart_v1_to_v2(raw)

        assert migrated["data_series"][0]["style"] == {"color": "#112233"}

    def test_extracts_vector_style_fields_only(self):
        raw = {
            "chart_type": "vector",
            "data_series": [{
                "dataset_id": "ds1", "x_column": "x", "y_column": "y",
                "vector_color": "#abcdef", "vector_scale": 2.0, "vector_width": 0.01,
                "vector_head_width": 4.0, "vector_head_length": 6.0, "vector_head_axis_length": 5.0,
                "vector_colormap": "viridis",
            }],
        }

        migrated = migrate_chart_v1_to_v2(raw)

        assert migrated["data_series"][0]["style"] == {
            "vector_color": "#abcdef", "vector_colormap": "viridis",
            "vector_scale": 2.0, "vector_width": 0.01,
            "vector_head_width": 4.0, "vector_head_length": 6.0, "vector_head_axis_length": 5.0,
        }

    def test_leaves_original_flat_fields_untouched(self):
        raw = {
            "chart_type": "line",
            "data_series": [{"dataset_id": "ds1", "x_column": "x", "y_column": "y", "color": "#112233"}],
        }

        migrated = migrate_chart_v1_to_v2(raw)

        assert migrated["data_series"][0]["color"] == "#112233"
        assert migrated["data_series"][0]["dataset_id"] == "ds1"

    def test_does_not_mutate_the_input_dict(self):
        raw = {
            "chart_type": "line",
            "data_series": [{"dataset_id": "ds1", "x_column": "x", "y_column": "y", "color": "#112233"}],
        }

        migrate_chart_v1_to_v2(raw)

        assert "series_type" not in raw["data_series"][0]

    def test_handles_a_chart_with_no_series(self):
        raw = {"chart_type": "line", "data_series": []}

        migrated = migrate_chart_v1_to_v2(raw)

        assert migrated["data_series"] == []

    def test_defaults_missing_data_series_key_to_empty(self):
        raw = {"chart_type": "line"}

        migrated = migrate_chart_v1_to_v2(raw)

        assert migrated["data_series"] == []


class TestMigrateChartV2ToV3:
    """The real v2->v3 per-item migration: moves each fit's flat
    color/line_style/line_width/alpha fields into a nested "style" dict,
    the same shape data_series already got in v1->v2. Unlike v1->v2, this
    migration removes the old flat fields once moved (there's no
    consumer left that still needs them once FitData.style is
    authoritative)."""

    def test_migrate_chart_v2_to_v3_moves_fit_style_fields_into_a_nested_style_dict(self):
        raw = {
            "chart_type": "line",
            "data_series": [],
            "fit_data": [{
                "source_dataset_id": "ds1", "fit_type": "linear",
                "color": "#112233", "line_style": "dotted", "line_width": 3.0, "alpha": 0.5,
                "confidence_lower": [1.0], "confidence_upper": [2.0],
            }],
        }

        migrated = migrate_chart_v2_to_v3(raw)

        fit = migrated["fit_data"][0]
        assert fit["style"] == {"color": "#112233", "line_style": "dotted", "line_width": 3.0, "alpha": 0.5}
        assert "color" not in fit
        assert "line_style" not in fit
        assert "line_width" not in fit
        assert "alpha" not in fit
        assert fit["confidence_lower"] == [1.0]  # untouched
        assert fit["confidence_upper"] == [2.0]  # untouched

    def test_migrate_chart_v2_to_v3_handles_a_fit_missing_some_style_fields(self):
        raw = {"chart_type": "line", "data_series": [],
               "fit_data": [{"source_dataset_id": "ds1", "fit_type": "linear"}]}

        migrated = migrate_chart_v2_to_v3(raw)

        assert migrated["fit_data"][0]["style"] == {}

    def test_handles_a_chart_with_no_fit_data(self):
        raw = {"chart_type": "line", "data_series": []}

        migrated = migrate_chart_v2_to_v3(raw)

        assert migrated["fit_data"] == []

    def test_does_not_mutate_the_input_dict(self):
        raw = {
            "chart_type": "line",
            "data_series": [],
            "fit_data": [{"source_dataset_id": "ds1", "fit_type": "linear", "color": "#112233"}],
        }

        migrate_chart_v2_to_v3(raw)

        assert "style" not in raw["fit_data"][0]


def test_style_field_names_match_the_real_style_dataclasses():
    """Guards against pandaplot/models/migrations/per_item/chart.py's
    _STYLE_FIELDS_BY_CHART_TYPE silently drifting out of sync with the
    real style dataclasses (pandaplot/models/chart/series_style/) -- a
    drift here produces a TypeError at project-load time that gets
    silently swallowed by ProjectDataManager._load_item()'s bare except,
    dropping the whole chart from the loaded project."""
    import dataclasses

    from pandaplot.models.chart.series_type import SeriesType
    from pandaplot.models.chart.series_type_spec import SERIES_TYPE_SPECS
    from pandaplot.models.migrations.per_item.chart import _STYLE_FIELDS_BY_CHART_TYPE

    for series_type, spec in SERIES_TYPE_SPECS.items():
        expected = {f.name for f in dataclasses.fields(spec.style_cls)}
        actual = set(_STYLE_FIELDS_BY_CHART_TYPE[series_type.value])
        assert actual == expected, f"{series_type.value}: {actual} != {expected}"
