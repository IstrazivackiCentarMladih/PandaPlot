# Per-Series "None" Line Style

## Problem

A chart's overall rendering mode (`Chart.chart_type`: `"line"` / `"scatter"` / `"bar"` / `"hist"`) applies to every data series in the chart uniformly. `DataSeries` already supports hiding a series' marker (`MarkerType.NONE`), but there is no equivalent way to hide a series' *line* while keeping its markers. This means a user cannot have one series drawn as a connected line and another series in the same chart drawn as markers-only ("scatter look") without switching the entire chart to the `"scatter"` chart type (which then forces *all* series to render via `ax.scatter()`).

## Goal

Add a `"None"` option to the per-series line style so an individual series can render as markers-only inside a chart that is still typed `"line"`. The chart-level `"scatter"` type is untouched and continues to exist for when every series in the chart should be scatter-rendered.

## Non-goals

- Removing or merging the chart-level `"scatter"` type.
- Any change to `MarkerType`, fit-line rendering, or bar/histogram rendering.
- Any project-file migration — `"none"` is simply a new valid string value for `DataSeries.line_style`; existing saved charts are unaffected and keep defaulting to `"solid"`.

## Design

### 1. `LineStyleType` enum

File: `pandaplot/models/chart/chart_configuration.py`

Add a new member:

```python
class LineStyleType(Enum):
    SOLID = "solid"
    DASHED = "dashed"
    DOTTED = "dotted"
    DASHDOT = "dashdot"
    NONE = "none"
```

`LineStyle.to_matplotlib_kwargs()` already forwards `self.style.value` unchanged into the `linestyle` kwarg. Matplotlib natively accepts the long-form string `"none"` to mean "draw no line" (equivalent to `linestyle=""`), so this method needs no code change — it already round-trips the new value correctly.

### 2. Chart preview rendering

File: `pandaplot/gui/components/tabs/chart/chart_editor.py`

`update_chart()` builds a local `_linestyle_map` translating the model's short string keys to matplotlib linestyle codes:

```python
_linestyle_map = {
    "solid": "-", "dashed": "--", "dotted": ":", "dashdot": "-.",
}
```

Add an entry so the "none" value passes through as matplotlib's "no line" spec:

```python
_linestyle_map = {
    "solid": "-", "dashed": "--", "dotted": ":", "dashdot": "-.", "none": "none",
}
```

This dict is used by every `ax.plot(...)` call in `update_chart()` (the primary data-series branch and the two fallback branches for missing dataset/column), so a single change covers all of them. `marker=` is passed independently in the same call, so a series with `line_style="none"` and `marker_style="circle"` (or any non-none marker) renders as markers-only, with no other code path affected.

No change is needed in `_plot_data`/`_plot_line` in `chart_style_manager.py` — that module already forwards the raw enum value and is not currently wired into the live chart-preview rendering path (only used for `get_default_configuration()` in the properties panel and its own now-unused `create_preview`); it stays correct by construction once the enum member exists.

### 3. Properties panel UI

File: `pandaplot/gui/components/sidebar/chart/chart_properties_panel.py`

`line_style_combo` is populated generically:

```python
for style in LineStyleType:
    self.line_style_combo.addItem(style.value.title(), style)
```

No widget code changes are required — adding the enum member makes "None" appear in the dropdown automatically. Selecting it flows through the existing `_on_style_changed` / `apply_to_chart` wiring, which already does:

```python
series.line_style = self.line_style_combo.currentData().value
```

so `series.line_style` becomes `"none"` with zero additional wiring.

### Edge case: line and marker both "None"

If a user sets both `line_style="none"` and `marker_style="none"` on the same series, that series renders nothing. This is an accepted, pre-existing class of footgun (already possible today via marker-none plus a barely visible line) and is not specially guarded against.

## Testing

- Add/extend a unit test asserting that a `DataSeries` with `line_style="none"` produces matplotlib call kwargs (or an equivalent lookup via the `_linestyle_map`) equal to `"none"`, and that it composes correctly with a non-none `marker_style`.
- Manually verify in the running app: create a chart with two series, set one series' Line Style to "None" with Marker Style "Circle", confirm it renders as scatter points while the sibling series (Line Style "Solid") still renders as a connected line, within the same "Line"-typed chart.
