"""Live preview renderer for the chart wizard's Labels step.

Deliberately a *small, self-contained* renderer, not a reuse of
`ChartEditorWidget.update_chart()` (the app's real chart-rendering path):
that method is ~500 lines tightly bound to a persisted `Chart` object, a live
`ChartEditorWidget`, and its own zoom/pan/toolbar state -- pulling it in here
would mean either a large extraction refactor of the main rendering path, or
embedding a full editor widget in a tiny preview pane. This function plots
real series data (via the same `resolve_series_data` the real renderer uses)
with a deliberately simplified subset of styling: default matplotlib
line/scatter/bar/hist plotting, a title/subtitle, axis labels, and on/off
legend and grid -- everything the wizard's Labels step actually exposes.
Anything else (per-series color/style, legend position, grid color, ...) is
still only ever set via Chart Properties after Finish, exactly as today.
"""
from pandaplot.gui.components.tabs.chart.chart_canvas import ChartCanvas
from pandaplot.gui.components.tabs.chart.chart_editor import resolve_series_data
from pandaplot.models.project.items.chart import DataSeries

_SAMPLE_X = [1, 2, 3, 4, 5]
_SAMPLE_Y = [2, 3, 1, 4, 3]


def render_wizard_preview(
    canvas: ChartCanvas, project, chart_type: str, series_configs: list[dict],
    title: str, subtitle: str, x_label: str, y_label: str,
    show_legend: bool, show_grid: bool,
) -> None:
    axes = canvas.axes
    axes.clear()

    any_plotted = False
    for config in series_configs:
        series = DataSeries(
            dataset_id=config["dataset_id"],
            x_column_id=config.get("x_column_id", ""),
            y_column_id=config.get("y_column_id", ""),
            x_error_column_id=config.get("x_error_column_id", ""),
            y_error_column_id=config.get("y_error_column_id", ""),
            error_symmetric=config.get("error_symmetric", True),
        )
        data = resolve_series_data(project, series, chart_type)
        if data.error is not None:
            continue
        any_plotted = True
        label = config.get("dataset_id", "") or None
        if chart_type == "line":
            axes.plot(data.x_data, data.y_data, label=label)
        elif chart_type == "scatter":
            axes.scatter(data.x_data, data.y_data, label=label)
        elif chart_type == "bar":
            axes.bar(data.x_data, data.y_data, label=label)
        elif chart_type == "hist":
            axes.hist(data.y_data, bins=10, label=label)

    if not any_plotted:
        # No resolvable series yet (wizard just opened, or the user hasn't
        # picked columns) -- fall back to the same sample data the Type
        # step's own preview uses, so the panel never renders empty axes.
        if chart_type == "line":
            axes.plot(_SAMPLE_X, _SAMPLE_Y)
        elif chart_type == "scatter":
            axes.scatter(_SAMPLE_X, _SAMPLE_Y)
        elif chart_type == "bar":
            axes.bar(_SAMPLE_X, _SAMPLE_Y)
        elif chart_type == "hist":
            axes.hist(_SAMPLE_Y, bins=5)

    axes.set_title(title)
    axes.set_xlabel(x_label)
    axes.set_ylabel(y_label)
    if subtitle:
        # Matplotlib has no built-in subtitle artist; a small secondary title
        # just below the main one reads close enough for a preview (the real
        # two-artist title+subtitle rendering stays in chart_editor.py).
        axes.text(0.5, 1.0, subtitle, transform=axes.transAxes,
                   ha="center", va="bottom", fontsize=8)
    if show_legend and any_plotted:
        axes.legend()
    axes.grid(show_grid)
    canvas.draw()
