"""Per-series-type styling capabilities: the single source of truth this
design introduces to replace the independently-drifting if/elif checks in
chart_editor.py's update_chart()/resolve_series_data() and style_tab.py's
_update_target_cards_visibility(). See test_series_type_spec.py for the
current hardcoded behavior each field's value is derived from.

Deliberately holds no matplotlib-dependent render callable -- pandaplot/models/
has zero matplotlib imports today, and this keeps it that way. The actual
per-type render functions live in the GUI layer (a later phase), keyed by
the same SeriesType.
"""
from dataclasses import dataclass
from typing import Literal

from pandaplot.models.chart.series_type import SeriesType


@dataclass(frozen=True)
class SeriesTypeSpec:
    marker_mode: Literal["required", "optional", "unsupported"]
    supports_line_style: bool
    supports_fill: bool
    supports_error_bars: bool
    needs_x_column: bool
    needs_secondary_columns: bool


SERIES_TYPE_SPECS: dict[SeriesType, SeriesTypeSpec] = {
    SeriesType.LINE: SeriesTypeSpec(
        marker_mode="optional", supports_line_style=True, supports_fill=True,
        supports_error_bars=True, needs_x_column=True, needs_secondary_columns=False,
    ),
    SeriesType.SCATTER: SeriesTypeSpec(
        marker_mode="required", supports_line_style=False, supports_fill=False,
        supports_error_bars=True, needs_x_column=True, needs_secondary_columns=False,
    ),
    SeriesType.BAR: SeriesTypeSpec(
        marker_mode="unsupported", supports_line_style=False, supports_fill=False,
        supports_error_bars=True, needs_x_column=True, needs_secondary_columns=False,
    ),
    SeriesType.HIST: SeriesTypeSpec(
        marker_mode="unsupported", supports_line_style=False, supports_fill=False,
        supports_error_bars=False, needs_x_column=False, needs_secondary_columns=False,
    ),
    SeriesType.VECTOR: SeriesTypeSpec(
        marker_mode="unsupported", supports_line_style=False, supports_fill=False,
        supports_error_bars=False, needs_x_column=True, needs_secondary_columns=True,
    ),
}
