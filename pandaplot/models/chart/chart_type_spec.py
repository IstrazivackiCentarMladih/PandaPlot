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
        allowed_series_types=frozenset({SeriesType.LINE, SeriesType.SCATTER}),
        allows_fit=True, default_series_type=SeriesType.LINE,
    ),
    ChartType.SCATTER: ChartTypeSpec(
        display_name="Scatter", roles=("x", "y"), required_roles=("y",),
        allowed_series_types=frozenset({SeriesType.SCATTER}),
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
        allowed_series_types=frozenset({SeriesType.VECTOR, SeriesType.LINE}),
        allows_fit=True, default_series_type=SeriesType.VECTOR,
    ),
}


def get_chart_type_spec(chart_type: "str | ChartType") -> ChartTypeSpec:
    """Return the spec for `chart_type`.

    Raises:
        ValueError: if `chart_type` is not one of the 5 supported types.
    """
    return CHART_TYPE_SPECS[ChartType(chart_type)]
