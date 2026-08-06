"""Per-chart-type column-role requirements for the chart creation wizard.

Chart-type strings mirror the literals `chart_editor.py` checks against
(`chart.chart_type == "line" / "scatter" / "bar" / "hist"`), not the
`ChartType` enum in `chart_configuration.py` (whose `HISTOGRAM = "histogram"`
value the renderer never checks) — the wizard must always emit `"hist"`.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class ChartRoleSpec:
    """Which column roles a chart type needs, and whether it renders error bars."""
    chart_type: str
    display_name: str
    roles: tuple[str, ...]
    required_roles: tuple[str, ...]
    supports_error_bars: bool


CHART_ROLE_SPECS: dict[str, ChartRoleSpec] = {
    "line": ChartRoleSpec("line", "Line", roles=("x", "y"), required_roles=("y",), supports_error_bars=True),
    "scatter": ChartRoleSpec("scatter", "Scatter", roles=("x", "y"), required_roles=("y",), supports_error_bars=True),
    "bar": ChartRoleSpec("bar", "Bar", roles=("x", "y"), required_roles=("y",), supports_error_bars=True),
    "hist": ChartRoleSpec("hist", "Histogram", roles=("values",), required_roles=("values",), supports_error_bars=False),
    # Color-mapped charts add a Z (color) role; all three columns are required
    # since there's nothing to map without them. No error bars.
    "colormap": ChartRoleSpec(
        "colormap", "Color Map", roles=("x", "y", "z"),
        required_roles=("x", "y", "z"), supports_error_bars=False),
    "heatmap": ChartRoleSpec(
        "heatmap", "Heatmap", roles=("x", "y", "z"),
        required_roles=("x", "y", "z"), supports_error_bars=False),
}


def get_chart_role_spec(chart_type: str) -> ChartRoleSpec:
    """Return the role spec for `chart_type`.

    Raises:
        KeyError: if `chart_type` is not one of the wizard's 4 supported types.
    """
    return CHART_ROLE_SPECS[chart_type]
