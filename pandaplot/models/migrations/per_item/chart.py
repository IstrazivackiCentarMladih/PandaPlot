"""Per-item migrations for chart raw dicts.

Pure dict -> dict transforms, run before Chart.from_dict() constructs the
object -- unlike cross-item migrations (see migrations/cross_item/),
these cannot look up another item's data (e.g. a dataset), only reshape
the chart's own dict.
"""
from typing import Callable

from pandaplot.models.migrations.schema_version import CURRENT_SCHEMA_VERSION

# Which of a v1 series' flat fields belong in the new "style" sub-object,
# per chart type. Mirrors pandaplot.models.chart.series_style's 5 typed
# classes exactly (LineSeriesStyle/ScatterSeriesStyle/BarSeriesStyle/
# HistSeriesStyle/VectorSeriesStyle) -- kept as plain tuples of field
# names here, rather than importing those classes, since this module only
# ever produces plain dicts (Chart.from_dict is what turns a "style" dict
# into a real dataclass instance, using the same field names).
_STYLE_FIELDS_BY_CHART_TYPE: dict[str, tuple[str, ...]] = {
    "line": (
        "color", "marker_color", "marker_edge_color", "marker_edge_width",
        "line_style", "marker_style", "line_width", "marker_size",
        "fill_enabled", "fill_color", "fill_alpha", "fill_orientation",
        "fill_base", "fill_to_index",
    ),
    "scatter": (
        "color", "marker_color", "marker_edge_color", "marker_edge_width",
        "marker_style", "marker_size",
    ),
    "bar": ("color",),
    "hist": ("color",),
    "vector": (
        "vector_color", "vector_colormap", "vector_scale", "vector_width",
        "vector_head_width", "vector_head_length", "vector_head_axis_length",
    ),
}


def migrate_chart_v1_to_v2(raw: dict) -> dict:
    """Add series_type + style keys to each series, derived from the
    chart's chart_type and that series' own flat fields. Every existing
    key is left in place -- this migration only adds data, it does not
    remove any (removal is a later sub-phase's job, once every consumer
    reads from the new fields instead)."""
    chart_type = raw.get("chart_type", "line")
    style_field_names = _STYLE_FIELDS_BY_CHART_TYPE.get(chart_type, _STYLE_FIELDS_BY_CHART_TYPE["line"])

    migrated_series = []
    for series in raw.get("data_series", []):
        new_series = dict(series)
        new_series["series_type"] = chart_type
        new_series["style"] = {name: series[name] for name in style_field_names if name in series}
        migrated_series.append(new_series)

    new_raw = dict(raw)
    new_raw["data_series"] = migrated_series
    return new_raw


_FIT_STYLE_FIELDS = ("color", "line_style", "line_width", "alpha")


def migrate_chart_v2_to_v3(raw: dict) -> dict:
    """v2 -> v3: move each fit's flat color/line_style/line_width/alpha
    fields into a nested "style" dict, matching v1->v2's identical move
    for data_series. confidence_lower/confidence_upper are untouched --
    they were already correct, just never had a UI to control how their
    band renders (see FitStyle.band_fill_enabled/band_fill_alpha/
    band_color, new in this version)."""
    new_raw = dict(raw)
    new_fit_data = []
    for fit in raw.get("fit_data", []):
        new_fit = dict(fit)
        new_fit["style"] = {
            name: fit[name] for name in _FIT_STYLE_FIELDS if name in fit
        }
        for name in _FIT_STYLE_FIELDS:
            new_fit.pop(name, None)
        new_fit_data.append(new_fit)
    new_raw["fit_data"] = new_fit_data
    return new_raw


PER_ITEM_CHART_MIGRATIONS: dict[int, Callable[[dict], dict]] = {
    1: migrate_chart_v1_to_v2,
    2: migrate_chart_v2_to_v3,
}


def migrate_chart(raw: dict, schema_version: int) -> dict:
    while schema_version < CURRENT_SCHEMA_VERSION:
        migrate = PER_ITEM_CHART_MIGRATIONS.get(schema_version)
        if migrate is not None:
            raw = migrate(raw)
        schema_version += 1
    return raw
