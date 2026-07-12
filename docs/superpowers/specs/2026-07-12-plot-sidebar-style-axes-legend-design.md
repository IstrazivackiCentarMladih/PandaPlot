# Fix and Extend Plot Sidebar: Style / Axes / Legend

## Problem

The chart properties sidebar (`ChartPropertiesPanel`, `pandaplot/gui/components/sidebar/chart/chart_properties_panel.py`) has Style, Axes, and Legend tabs. Several of their fields don't do anything to the rendered chart:

- **Two "Show Grid" checkboxes** (one in the X Axis group, one in the Y Axis group) both write into a single `chart.config["show_grid"]` boolean via a logical AND (`_on_chart_config_changed` line 918, `apply_to_chart` line 1333), and both get reloaded from that same combined value (`load_chart_object` lines 1306-1307). There is no real per-axis grid — `chart_editor.py` makes one `axes.grid(True/False)` call (lines 516-518) that affects both axes together. Net effect: unchecking either checkbox kills the whole grid, and the two checkboxes visually decouple from what actually happened, which reads as "one of them doesn't work."
- **Line Transparency**, **X/Y Font Size**, **X/Y Scale (log/linear)**, **Legend Position**, **Legend Font Size**, and **Legend Background** are all no-ops in the running app. They connect only to a parallel, unused model (`ChartConfiguration`/`AxisStyle`/`LegendStyle` in `pandaplot/models/chart/chart_configuration.py` and `ChartStyleManager` in `pandaplot/models/chart/chart_style_manager.py`) via `_get_current_configuration()`/`_load_configuration()`/`load_chart()`, none of which are reachable at runtime (`load_chart()` guards on `hasattr(project, "charts")`, which is never true — charts live in the project's item tree, not a `charts` attribute). The actual rendering path (`ChartEditorWidget.update_chart()` in `chart_editor.py`) reads only from `chart.config` (a plain dict) and `DataSeries`/`FitData`, and never touches `ChartConfiguration`.
- There is no way to set axis min/max limits or control tick placement/format, even though `AxisStyle` (in the dead model) already has `min_limit`/`max_limit`/`auto_limits` fields — just not reachable from the live rendering code.

## Goal

1. Make every field currently shown in the Style, Axes, and Legend tabs actually affect the rendered chart, wired through the live model (`chart.config` dict + `DataSeries`) that `chart_editor.py` already reads.
2. Fix "Show Grid" so X and Y are truly independent controls.
3. Add new controls for X/Y axis limits (auto or manual min/max) and X/Y tick configuration (auto/fixed-count/fixed-step placement, plus a label format).

## Non-goals

- Touching the dead `ChartConfiguration`/`AxisStyle`/`LegendStyle`/`ChartStyleManager` classes or the unreachable `load_chart()`/`_get_current_configuration()`/`_load_configuration()` methods in the panel. They stay as-is; removing them is a separate future cleanup.
- Any project-file migration. All new `chart.config` keys are read with `.get(key, default)`, so existing saved charts without these keys keep rendering exactly as they do today (auto-scaled axes, linear scale, existing grid/legend behavior preserved as closely as the per-axis grid split allows — see below).
- Changing chart types, series data handling, or anything outside the Style/Axes/Legend tabs.

## Design

### 1. Data model changes

**File: `pandaplot/models/project/items/chart.py`**

`DataSeries` gets one new field:

```python
alpha: float = 1.0
```

Added to the dataclass (after `marker_size`), and to both `to_dict()` (serialize `"alpha": series.alpha`) and `from_dict()` (`alpha=series_dict.get("alpha", 1.0)`) so it round-trips through project save/load like every other `DataSeries` field.

`Chart._init_default_config()` replaces `"show_grid": True` with independent per-axis keys and adds the new limit/tick/legend-frame keys:

```python
self.config = {
    "title": self.name,
    "x_label": "",
    "y_label": "",
    "show_legend": True,
    "legend_position": "upper right",
    "legend_show_frame": True,
    "legend_font_size": 10,
    "legend_bg_color": "#ffffff",
    "grid_style": "solid",
    "grid_alpha": 0.3,
    "show_grid_x": True,
    "show_grid_y": True,
    "x_font_size": 12,
    "y_font_size": 12,
    "x_scale": "linear",
    "y_scale": "linear",
    "x_auto_limits": True,
    "y_auto_limits": True,
    "x_min": 0.0,
    "x_max": 1.0,
    "y_min": 0.0,
    "y_max": 1.0,
    "x_tick_mode": "auto",
    "y_tick_mode": "auto",
    "x_tick_count": 5,
    "y_tick_count": 5,
    "x_tick_step": 1.0,
    "y_tick_step": 1.0,
    "x_tick_format": "auto",
    "y_tick_format": "auto",
    "x_tick_format_custom": "",
    "y_tick_format_custom": "",
}
```

Because `Chart.config` is already a loose `Dict[str, Any]` serialized wholesale (`to_dict` line 302: `"config": self.config`), no `to_dict`/`from_dict` changes are needed for these keys — they ride along automatically. `from_dict` already calls `chart._init_default_config()` when `config` is empty (line 366-367); for charts saved *before* this change (config present but missing the new keys), every read site in `chart_editor.py` uses `.get(key, default)`, so old charts render identically to today until the user touches the new controls.

The old single `"show_grid"` key is removed from the default config. `get_config_summary()` (line 238: `"has_grid": self.config.get("show_grid", True)`) changes to `self.config.get("show_grid_x", True) or self.config.get("show_grid_y", True)`.

### 2. Fixing "Show Grid" (independent X/Y)

**File: `pandaplot/gui/components/sidebar/chart/chart_properties_panel.py`**

- `_on_chart_config_changed` (line 917-918) changes from the AND-into-one-key to two independent writes:
  ```python
  if hasattr(self, "x_grid_check"):
      config["show_grid_x"] = self.x_grid_check.isChecked()
  if hasattr(self, "y_grid_check"):
      config["show_grid_y"] = self.y_grid_check.isChecked()
  ```
- `apply_to_chart` (line 1333) gets the same two-key split.
- `load_chart_object` (lines 1306-1307) loads each checkbox from its own key:
  ```python
  self.x_grid_check.setChecked(config.get("show_grid_x", True))
  self.y_grid_check.setChecked(config.get("show_grid_y", True))
  ```

**File: `pandaplot/gui/components/tabs/chart/chart_editor.py`**

Lines 516-518 (single `axes.grid(...)` call) become two separate calls, one per axis:

```python
self.chart_canvas.axes.grid(
    config.get("show_grid_x", True), axis="x", alpha=config.get("grid_alpha", 0.3))
self.chart_canvas.axes.grid(
    config.get("show_grid_y", True), axis="y", alpha=config.get("grid_alpha", 0.3))
```

Matplotlib's `Axes.grid(b, axis=...)` supports independently enabling/disabling gridlines per axis, so this is a direct fix with no further plumbing.

### 3. Style tab — Line Transparency

**File: `pandaplot/gui/components/sidebar/chart/chart_properties_panel.py`**

- `_on_style_changed` (around line 874, alongside `line_width`/`marker_size`) adds:
  ```python
  series.alpha = self.line_transparency_spin.value()
  ```
- `apply_to_chart` (around line 1362) adds the same assignment.
- `load_chart_object`, where style controls are populated from the first series (around line 1293), adds:
  ```python
  self.line_transparency_spin.setValue(first_series.alpha)
  ```

**File: `pandaplot/gui/components/tabs/chart/chart_editor.py`**

Every plot call currently hardcodes `alpha=1.0 if series.visible else 0.3` (lines 438, 448, 453) or `0.7 if series.visible else 0.3` for histograms (line 458). These become:

```python
alpha=series.alpha if series.visible else 0.3
```

so the transparency spinbox controls real opacity when the series is visible, while the existing "dim to 0.3 when hidden" behavior (an unrelated, pre-existing visibility cue) is preserved unchanged. The fallback/"column not found" and "dataset not found" branches (lines 477, 496) keep their existing fixed `alpha=0.5` — those are error-state renders, not the user's own series, and are out of scope.

### 4. Axes tab — Font Size and Scale

**File: `pandaplot/gui/components/sidebar/chart/chart_properties_panel.py`**

`_connect_signals` (around line 656-658) adds:
```python
self.x_font_size_spin.valueChanged.connect(self._on_chart_config_changed)
self.x_scale_combo.currentIndexChanged.connect(self._on_chart_config_changed)
self.y_font_size_spin.valueChanged.connect(self._on_chart_config_changed)
self.y_scale_combo.currentIndexChanged.connect(self._on_chart_config_changed)
```

`_on_chart_config_changed` and `apply_to_chart` add:
```python
config["x_font_size"] = self.x_font_size_spin.value()
config["y_font_size"] = self.y_font_size_spin.value()
config["x_scale"] = self.x_scale_combo.currentData().value  # ScaleType enum -> "linear"/"log"
config["y_scale"] = self.y_scale_combo.currentData().value
```

`load_chart_object` sets the widgets from config the same way the grid checkboxes are loaded.

**File: `pandaplot/gui/components/tabs/chart/chart_editor.py`**

After the existing `set_xlabel`/`set_ylabel` calls (lines 513-514), add scale and font size application:

```python
self.chart_canvas.axes.set_xscale(config.get("x_scale", "linear"))
self.chart_canvas.axes.set_yscale(config.get("y_scale", "linear"))
self.chart_canvas.axes.xaxis.label.set_size(config.get("x_font_size", 12))
self.chart_canvas.axes.yaxis.label.set_size(config.get("y_font_size", 12))
```

Per the approved design, font size controls only the axis *label* size (not tick labels), matching the "Font Size" field being grouped with "Label" in the UI.

Log scale is only valid for strictly positive data; matplotlib silently clips non-positive values with a warning rather than crashing, so no extra guard is added — this matches matplotlib's normal behavior elsewhere in the app.

### 5. Axes tab — new Limits section (per X/Y group)

**UI** (`_create_axes_tab`, extending the X Axis / Y Axis `QGroupBox` layouts after the existing Scale row and before Show Grid):

- `x_auto_limits_check` (`QCheckBox("Auto")`, default checked)
- `x_min_spin`, `x_max_spin` (`QDoubleSpinBox`, wide range e.g. -1e9..1e9, disabled while Auto is checked)
- Mirrored `y_auto_limits_check`, `y_min_spin`, `y_max_spin`

Toggling the Auto checkbox both writes config and enables/disables the min/max spinboxes:
```python
self.x_auto_limits_check.toggled.connect(self._on_x_auto_limits_toggled)
```
```python
def _on_x_auto_limits_toggled(self, checked):
    self.x_min_spin.setEnabled(not checked)
    self.x_max_spin.setEnabled(not checked)
    self._on_chart_config_changed()
```
(mirrored for Y). All three widgets' change signals connect to `_on_chart_config_changed` as usual.

**Config writes** (`_on_chart_config_changed`, `apply_to_chart`):
```python
config["x_auto_limits"] = self.x_auto_limits_check.isChecked()
config["x_min"] = self.x_min_spin.value()
config["x_max"] = self.x_max_spin.value()
```
(mirrored for y).

**Load** (`load_chart_object`): set checkbox + spinboxes from config, and call the same enable/disable logic as the toggle handler so the initial widget-enabled state matches the loaded value.

**Rendering** (`chart_editor.py`, after the scale/font-size block):
```python
if not config.get("x_auto_limits", True):
    self.chart_canvas.axes.set_xlim(config.get("x_min", 0.0), config.get("x_max", 1.0))
if not config.get("y_auto_limits", True):
    self.chart_canvas.axes.set_ylim(config.get("y_min", 0.0), config.get("y_max", 1.0))
```
When auto is on (the default, matching today's behavior), no `set_xlim`/`set_ylim` call is made and matplotlib autoscales exactly as it does today.

Note: `chart_canvas.store_original_limits()` (line 525, used by the zoom/pan reset button) is called after this block already, so "reset zoom" naturally resets to the user's configured manual limits when auto-limits is off, or to the autoscaled view when it's on — no change needed there.

### 6. Axes tab — new Ticks section (per X/Y group)

**UI** (added below the new Limits section, above Show Grid):

- `x_tick_mode_combo`: `QComboBox` with items "Auto", "Fixed Count", "Fixed Step" (mapped to config values `"auto"`, `"count"`, `"step"`)
- `x_tick_count_spin`: `QSpinBox` (range 2-50, default 5), enabled only when mode is "Fixed Count"
- `x_tick_step_spin`: `QDoubleSpinBox` (default 1.0), enabled only when mode is "Fixed Step"
- `x_tick_format_combo`: `QComboBox` with items "Auto", "Integer", "1 Decimal", "2 Decimals", "Scientific", "Custom..." (mapped to `"auto"`, `"integer"`, `"1decimal"`, `"2decimal"`, `"scientific"`, `"custom"`)
- `x_tick_format_custom_edit`: `QLineEdit`, visible/enabled only when format is "Custom...", holding a Python format spec (e.g. `"{:.2f} units"`)
- Mirrored `y_*` widgets

`x_tick_mode_combo.currentIndexChanged` and `x_tick_format_combo.currentIndexChanged` handlers toggle the enabled/visible state of the dependent spinbox/text field (same pattern as the Auto-limits checkbox) and call `_on_chart_config_changed`.

**Config writes**: `x_tick_mode`, `x_tick_count`, `x_tick_step`, `x_tick_format`, `x_tick_format_custom` (and `y_*` equivalents) written in `_on_chart_config_changed`/`apply_to_chart`, loaded in `load_chart_object` (with the same enable/disable sync as on toggle).

**Rendering** (`chart_editor.py`, after the limits block), a small helper applied to each axis:

```python
from matplotlib.ticker import MaxNLocator, MultipleLocator, FuncFormatter

def _apply_ticks(axis, mode, count, step, fmt, custom_fmt):
    if mode == "count":
        axis.set_major_locator(MaxNLocator(nbins=count))
    elif mode == "step":
        axis.set_major_locator(MultipleLocator(step))
    # "auto" -> leave matplotlib's default locator in place

    if fmt == "integer":
        axis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:.0f}"))
    elif fmt == "1decimal":
        axis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:.1f}"))
    elif fmt == "2decimal":
        axis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:.2f}"))
    elif fmt == "scientific":
        axis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:.2e}"))
    elif fmt == "custom" and custom_fmt:
        def _safe_custom(v, _, _fmt=custom_fmt):
            try:
                return _fmt.format(v)
            except (ValueError, IndexError, KeyError):
                return str(v)
        axis.set_major_formatter(FuncFormatter(_safe_custom))
    # "auto" -> leave matplotlib's default formatter in place

_apply_ticks(self.chart_canvas.axes.xaxis, config.get("x_tick_mode", "auto"),
             config.get("x_tick_count", 5), config.get("x_tick_step", 1.0),
             config.get("x_tick_format", "auto"), config.get("x_tick_format_custom", ""))
_apply_ticks(self.chart_canvas.axes.yaxis, config.get("y_tick_mode", "auto"),
             config.get("y_tick_count", 5), config.get("y_tick_step", 1.0),
             config.get("y_tick_format", "auto"), config.get("y_tick_format_custom", ""))
```

`_safe_custom` wraps every individual label's `.format()` call, so an invalid custom format string (e.g. mismatched braces) degrades that label to a plain string of the number instead of raising mid-render — the chart never crashes on bad user input.

### 7. Legend tab

**File: `pandaplot/gui/components/sidebar/chart/chart_properties_panel.py`**

`_connect_signals` adds:
```python
self.legend_position_combo.currentIndexChanged.connect(self._on_chart_config_changed)
self.legend_font_size_spin.valueChanged.connect(self._on_chart_config_changed)
self.legend_bg_color_button.colorChanged.connect(self._on_chart_config_changed)
self.legend_show_frame_check.toggled.connect(self._on_chart_config_changed)
```

New widget `legend_show_frame_check` (`QCheckBox("Show Frame")`, default checked) added to `_create_legend_tab` below Background.

`_on_chart_config_changed`/`apply_to_chart` add:
```python
config["legend_position"] = self.legend_position_combo.currentData().value  # e.g. "upper right"
config["legend_font_size"] = self.legend_font_size_spin.value()
config["legend_bg_color"] = self.legend_bg_color_button.get_color()
config["legend_show_frame"] = self.legend_show_frame_check.isChecked()
```

`load_chart_object` sets all four widgets from config.

**File: `pandaplot/gui/components/tabs/chart/chart_editor.py`**

Lines 520-522 (legend creation) become:
```python
if config.get("show_legend", True) and (self.chart.data_series or self.chart.fit_data):
    legend = self.chart_canvas.axes.legend(
        loc=config.get("legend_position", "upper right"),
        fontsize=config.get("legend_font_size", 10),
        facecolor=config.get("legend_bg_color", "#ffffff"),
        frameon=config.get("legend_show_frame", True))
```

### Summary of files touched

- `pandaplot/models/project/items/chart.py` — `DataSeries.alpha` field + serialization, new `chart.config` default keys, `get_config_summary()` grid key update.
- `pandaplot/gui/components/sidebar/chart/chart_properties_panel.py` — new widgets (limits, ticks, legend frame), new/updated signal connections, `_on_chart_config_changed`/`_on_style_changed`/`apply_to_chart`/`load_chart_object` read/write the new keys and fields.
- `pandaplot/gui/components/tabs/chart/chart_editor.py` — `update_chart()` applies scale, font size, limits, ticks, per-axis grid, alpha, and richer legend styling.

## Testing

- Unit tests around `Chart`/`DataSeries`: default config contains the new keys with documented defaults; `to_dict`/`from_dict` round-trips `DataSeries.alpha`; a `chart.config` dict missing the new keys (simulating an old save file) still produces the documented defaults via `.get()` at every read site.
- Manual verification in the running app for each fixed/new field:
  - Toggle X Show Grid and Y Show Grid independently; confirm gridlines appear/disappear per-axis rather than both-or-nothing.
  - Set Line Transparency to e.g. 0.4 on a series; confirm the rendered line/markers are visibly more transparent, and that toggling series visibility still dims to the existing "hidden" look.
  - Set X/Y Font Size and Scale (Log); confirm axis label size changes and the axis renders log-scaled.
  - Uncheck Auto under Limits, set explicit min/max; confirm the axis is clamped to that range and "reset zoom" returns to it (not to full autoscale).
  - Set Tick Mode to Fixed Count and Fixed Step; confirm tick spacing changes accordingly. Set Tick Format through each preset and through Custom with both a valid and an intentionally invalid format string; confirm the invalid one falls back to plain numbers instead of crashing the chart.
  - Change Legend Position, Font Size, Background, and toggle Show Frame; confirm the legend box updates accordingly.
  - Save and reopen the project; confirm every one of the above settings persists.
