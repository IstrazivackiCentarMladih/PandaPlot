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
from pandaplot.models.project.items import Dataset
from pandaplot.models.project.items.chart import DataSeries

_SAMPLE_X = [1, 2, 3, 4, 5]
_SAMPLE_Y = [2, 3, 1, 4, 3]


def _series_label(project, config: dict) -> str:
    """Readable legend label for a series, e.g. "{dataset name}:{Y column name}".

    Mirrors `CreateChartFromWizardCommand._default_series_label` so the
    preview's legend matches what the actually-created chart shows. Degrades
    gracefully to the raw dataset id if the project or dataset can't resolve
    it -- this is only a preview, never worth crashing over.
    """
    dataset_id = config.get("dataset_id", "")
    if project is None:
        return dataset_id
    dataset = project.find_item(dataset_id)
    if not isinstance(dataset, Dataset):
        return dataset_id
    y_column_id = config.get("y_column_id", "")
    y_column_name = ""
    if y_column_id:
        y_column_name = dataset.column_name(y_column_id) or ""
    return f"{dataset.name}:{y_column_name}" if y_column_name else dataset.name


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
            z_column_id=config.get("z_column_id", ""),
            x_error_column_id=config.get("x_error_column_id", ""),
            y_error_column_id=config.get("y_error_column_id", ""),
            error_symmetric=config.get("error_symmetric", True),
        )
        data = resolve_series_data(project, series, chart_type)
        if data.error is not None:
            continue
        label = _series_label(project, config)
        if chart_type == "line":
            axes.plot(data.x_data, data.y_data, label=label)
        elif chart_type == "scatter":
            axes.scatter(data.x_data, data.y_data, label=label)
        elif chart_type == "bar":
            axes.bar(data.x_data, data.y_data, label=label)
        elif chart_type == "hist":
            axes.hist(data.y_data, bins=10, label=label)
        elif chart_type == "colormap":
            axes.scatter(data.x_data, data.y_data, c=data.z_data, cmap="viridis")
        elif chart_type == "heatmap":
            from pandaplot.gui.components.tabs.chart.chart_heatmap import build_heatmap_grid
            try:
                xs, ys, grid = build_heatmap_grid(
                    data.x_data, data.y_data, data.z_data,
                    config.get("heatmap_gridding", "grid"),
                    config.get("heatmap_resolution", 50))
            except ValueError:
                continue
            axes.pcolormesh(xs, ys, grid, cmap="viridis", shading="nearest")
        any_plotted = True

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

    axes.set_title(f"{title}\n{subtitle}" if subtitle else title)
    axes.set_xlabel(x_label)
    axes.set_ylabel(y_label)
    if show_legend and any_plotted:
        axes.legend()
    axes.grid(show_grid)
    canvas.draw()
