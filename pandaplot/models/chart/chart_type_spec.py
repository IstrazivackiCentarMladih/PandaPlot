"""Per-chart-type column-role requirements and series-type allow-list.

Absorbs pandaplot/gui/dialogs/chart/chart_role_spec.py's ChartRoleSpec/
CHART_ROLE_SPECS (display_name/roles/required_roles, unchanged) into this
single registry rather than keeping two competing ones, and adds the
allowed_series_types/allows_fit/default_series_type fields nothing in the
codebase declared before. `allowed_series_types` is enforced by
`Chart.set_chart_type`, which retypes only the series that fall outside
the new chart type's allow-list, and by the "add series" flow -- mixed
series types are a real, working capability on a chart today.

supports_error_bars is a *property*, not a stored field: chart_role_spec.py
used to store this fact directly per chart type, but SeriesTypeSpec now
owns the single definition of which series types render error bars.
Storing it twice here would let the two silently drift again -- the exact
kind of duplication this whole design exists to eliminate.
"""
from dataclasses import dataclass

from pandaplot.models.chart.chart_type import ChartType
from pandaplot.models.chart.series_type import SeriesType
from pandaplot.models.chart.series_type_spec import SERIES_TYPE_SPECS


@dataclass(frozen=True)
class ChartTypeSpec:
    display_name: str
    roles: tuple[str, ...]
    required_roles: tuple[str, ...]
    # frozenset, not set: `frozen=True` on the dataclass only stops
    # `spec.allowed_series_types = ...` from reassigning the field -- a
    # plain `set` value is still mutable in place (`spec.allowed_series_
    # types.add(...)`), which would silently corrupt every chart using
    # this shared, module-level registry entry. frozenset closes that gap.
    allowed_series_types: frozenset[SeriesType]
    allows_fit: bool
    default_series_type: SeriesType

    @property
    def supports_error_bars(self) -> bool:
        return SERIES_TYPE_SPECS[self.default_series_type].supports_error_bars


CHART_TYPE_SPECS: dict[ChartType, ChartTypeSpec] = {
    ChartType.LINE: ChartTypeSpec(
        display_name="Line", roles=("x", "y"), required_roles=("y",),
        allowed_series_types=frozenset({SeriesType.LINE, SeriesType.SCATTER, SeriesType.VECTOR}),
        allows_fit=True, default_series_type=SeriesType.LINE,
    ),
    ChartType.SCATTER: ChartTypeSpec(
        display_name="Scatter", roles=("x", "y"), required_roles=("y",),
        allowed_series_types=frozenset({SeriesType.LINE, SeriesType.SCATTER, SeriesType.VECTOR}),
        allows_fit=True, default_series_type=SeriesType.SCATTER,
    ),
    ChartType.BAR: ChartTypeSpec(
        display_name="Bar", roles=("x", "y"), required_roles=("y",),
        allowed_series_types=frozenset({SeriesType.BAR, SeriesType.SCATTER}),
        allows_fit=True, default_series_type=SeriesType.BAR,
    ),
    ChartType.HIST: ChartTypeSpec(
        display_name="Histogram", roles=("values",), required_roles=("values",),
        allowed_series_types=frozenset({SeriesType.HIST}),
        allows_fit=True, default_series_type=SeriesType.HIST,
    ),
    ChartType.VECTOR: ChartTypeSpec(
        display_name="Vector", roles=("x", "y", "u", "v", "magnitude"),
        required_roles=("x", "y", "u", "v"),
        allowed_series_types=frozenset({SeriesType.LINE, SeriesType.SCATTER, SeriesType.VECTOR}),
        allows_fit=True, default_series_type=SeriesType.VECTOR,
    ),
    ChartType.COLORMAP: ChartTypeSpec(
        display_name="Color Map", roles=("x", "y", "z"), required_roles=("x", "y", "z"),
        allowed_series_types=frozenset({SeriesType.COLORMAP}),
        allows_fit=False, default_series_type=SeriesType.COLORMAP,
    ),
    ChartType.HEATMAP: ChartTypeSpec(
        display_name="Heatmap", roles=("x", "y", "z"), required_roles=("x", "y", "z"),
        allowed_series_types=frozenset({SeriesType.HEATMAP}),
        allows_fit=False, default_series_type=SeriesType.HEATMAP,
    ),
}


def compatible_chart_types(chart_type: "str | ChartType") -> frozenset[ChartType]:
    """Chart types it's non-destructive to switch `chart_type` into.

    `target` is compatible with `chart_type` iff `chart_type`'s own
    default_series_type is allowed on `target` -- i.e. the chart's
    "typical" series (what a freshly-created chart of that type actually
    has) survives the switch without a forced retype. This is a static
    per-type-pair rule, not dependent on any specific chart's actual
    series mix, so the chart-type selector UI can precompute it once per
    chart type rather than recomputing per chart. Always includes
    `chart_type` itself (switching a chart to its own current type is
    trivially non-destructive).
    """
    source_spec = CHART_TYPE_SPECS[ChartType(chart_type)]
    return frozenset(
        target for target, target_spec in CHART_TYPE_SPECS.items()
        if source_spec.default_series_type in target_spec.allowed_series_types
    )


def compatible_chart_types_for_series(series_types: "frozenset[SeriesType]") -> frozenset[ChartType]:
    """Chart types it's non-destructive to switch into, given the ACTUAL
    series types present on a chart -- not just the chart's nominal type's
    static default_series_type (see `compatible_chart_types`, which only
    looks at that).

    A target chart type is compatible iff EVERY one of `series_types` is
    already in that target's allowed_series_types, i.e. switching to it
    would force-retype NONE of the chart's existing series. An empty
    `series_types` (a brand-new, still-empty chart) has nothing to
    protect, so every chart type is compatible.

    Fixes a real gap in `compatible_chart_types`: a mixed chart -- e.g. a
    Scatter chart holding both SCATTER and VECTOR series -- would
    otherwise report Bar as a safe switch target (since SCATTER alone is
    allowed on Bar's {BAR, SCATTER}), silently retyping and discarding
    the VECTOR series' configuration on selection. Flagged in PR #180
    review.
    """
    types = frozenset(series_types)
    if not types:
        return frozenset(CHART_TYPE_SPECS.keys())
    return frozenset(
        target for target, spec in CHART_TYPE_SPECS.items()
        if types <= spec.allowed_series_types
    )


def get_chart_type_spec(chart_type: "str | ChartType") -> ChartTypeSpec:
    """Return the spec for `chart_type`.

    Raises:
        ValueError: if `chart_type` is not one of the 5 supported types.
    """
    return CHART_TYPE_SPECS[ChartType(chart_type)]
