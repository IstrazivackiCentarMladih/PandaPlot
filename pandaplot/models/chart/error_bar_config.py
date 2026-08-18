"""Error-bar column references and styling, shared by every series type
whose SeriesTypeSpec.supports_error_bars is True (today: LINE, SCATTER,
BAR). Extracted off DataSeries, which used to carry these 12 fields
flatly regardless of series type -- HIST and VECTOR series never had
error bars, so this composition means their style classes simply have
no error_bars field at all, rather than an always-present-but-unused one.
"""
from dataclasses import dataclass

from pandaplot.models.chart.error_direction import ErrorDirection


@dataclass
class ErrorBarConfig:
    x_error_column_id: str = ""
    y_error_column_id: str = ""
    x_error_minus_column_id: str = ""
    y_error_minus_column_id: str = ""
    # Legacy/fallback column names -- populated only by loading old
    # projects, mirroring DataSeries.x_column/y_column's own convention.
    x_error_column: str = ""
    y_error_column: str = ""
    x_error_minus_column: str = ""
    y_error_minus_column: str = ""
    error_symmetric: bool = True
    error_direction: ErrorDirection = ErrorDirection.BOTH
    error_color: str = ""  # "" => inherit the series' base color
    error_cap_size: float = 3.0

    def __post_init__(self):
        if isinstance(self.error_direction, str):
            self.error_direction = ErrorDirection(self.error_direction)

    @property
    def has_error_data(self) -> bool:
        """Whether any error-bar column is configured, by stable id
        (current data) or legacy name (old projects loaded before stable
        column ids)."""
        return bool(
            self.x_error_column_id or self.y_error_column_id
            or self.x_error_column or self.y_error_column
        )
