# Plot Sidebar Style/Axes/Legend Fix & Extension Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make every field in the chart properties sidebar's Style, Axes, and Legend tabs actually affect the rendered chart (fixing the "two Show Grid" bug and several silently-dead fields), and add new X/Y axis limit and tick controls.

**Architecture:** Extend the live model already read by the renderer — `Chart.config` (a plain dict) and `DataSeries` (a dataclass) in `pandaplot/models/project/items/chart.py` — with new keys/fields. Wire `ChartPropertiesPanel` (`pandaplot/gui/components/sidebar/chart/chart_properties_panel.py`) to read/write those keys instead of the dead `ChartConfiguration`/`ChartStyleManager` path. Apply everything in `ChartEditorWidget.update_chart()` (`pandaplot/gui/components/tabs/chart/chart_editor.py`), the single method that actually draws the matplotlib chart.

**Tech Stack:** PySide6 (Qt for Python) for the UI, matplotlib (via `FigureCanvasQTAgg`) for rendering, pytest for tests.

## Global Constraints

- No project-file migration: every new `chart.config` key is read with `.get(key, default)` everywhere, so charts saved before this change keep rendering exactly as they do today until a user touches a new control.
- Do not modify or remove the dead `ChartConfiguration`/`AxisStyle`/`LegendStyle`/`ChartStyleManager` classes or the unreachable `load_chart()`/`_get_current_configuration()`/`_load_configuration()` panel methods — out of scope per the approved spec (`docs/superpowers/specs/2026-07-12-plot-sidebar-style-axes-legend-design.md`).
- Follow existing test convention: tests live under `tests/`, mirroring `pandaplot/`, use plain pytest functions (no fixtures/classes), and do not instantiate real Qt widgets or `QApplication` — there is no `pytest-qt`/headless-Qt infrastructure in this repo, and this plan does not introduce any. GUI wiring changes that can't be expressed as widget-free unit tests are verified manually via the exact steps given in each task.
- Run tests with `pytest` from the repo root (`c:\vso\PandaPlot`).

---

### Task 1: Extend the Chart model — `DataSeries.alpha` and new `chart.config` keys

**Files:**
- Modify: `pandaplot/models/project/items/chart.py`
- Test: `tests/models/test_chart_style_axes_legend_config.py`

**Interfaces:**
- Produces: `DataSeries.alpha: float` (default `1.0`), serialized in `to_dict()`/`from_dict()`.
- Produces: new `Chart.config` default keys (all subsequent tasks read these via `chart.config.get(key, default)`):
  `show_grid_x`, `show_grid_y` (bool, default `True`; replaces the old single `show_grid`),
  `x_font_size`, `y_font_size` (int, default `12`),
  `x_scale`, `y_scale` (str `"linear"`/`"log"`, default `"linear"`),
  `x_auto_limits`, `y_auto_limits` (bool, default `True`),
  `x_min`, `x_max`, `y_min`, `y_max` (float, default `0.0`/`1.0`),
  `x_tick_mode`, `y_tick_mode` (str `"auto"`/`"count"`/`"step"`, default `"auto"`),
  `x_tick_count`, `y_tick_count` (int, default `5`),
  `x_tick_step`, `y_tick_step` (float, default `1.0`),
  `x_tick_format`, `y_tick_format` (str `"auto"`/`"integer"`/`"1decimal"`/`"2decimal"`/`"scientific"`/`"custom"`, default `"auto"`),
  `x_tick_format_custom`, `y_tick_format_custom` (str, default `""`),
  `legend_show_frame` (bool, default `True`), `legend_font_size` (int, default `10`), `legend_bg_color` (str, default `"#ffffff"`).
- Produces: `Chart.get_config_summary()["has_grid"]` now `True` if *either* `show_grid_x` or `show_grid_y` is `True`.

- [ ] **Step 1: Write the failing tests**

Create `tests/models/test_chart_style_axes_legend_config.py`:

```python
"""
Unit tests for the Chart/DataSeries model extensions backing the
Style/Axes/Legend sidebar tabs (per-axis grid, scale, font size,
axis limits, tick configuration, legend styling, series alpha).
"""

from pandaplot.models.project.items.chart import Chart, DataSeries


def test_data_series_alpha_defaults_to_fully_opaque():
    series = DataSeries(dataset_id="ds1", x_column="x", y_column="y")
    assert series.alpha == 1.0


def test_data_series_alpha_round_trips_through_serialization():
    chart = Chart(name="Test Chart", chart_type="line")
    chart.add_data_series(dataset_id="ds1", x_column="x", y_column="y", alpha=0.4)

    data = chart.to_dict()
    assert data["data_series"][0]["alpha"] == 0.4

    restored = Chart.from_dict(data)
    assert restored.data_series[0].alpha == 0.4


def test_data_series_alpha_defaults_when_missing_from_saved_data():
    # Simulates loading a project saved before the alpha field existed.
    data = {
        "id": "chart1",
        "name": "Test Chart",
        "chart_type": "line",
        "data_series": [{
            "dataset_id": "ds1", "x_column": "x", "y_column": "y", "label": "",
            "color": "#1f77b4", "marker_color": "", "marker_edge_color": "#000000",
            "line_style": "solid", "marker_style": "circle", "line_width": 2.0,
            "marker_size": 6.0, "visible": True,
        }],
        "fit_data": [],
        "config": {},
        "style": {},
    }

    restored = Chart.from_dict(data)
    assert restored.data_series[0].alpha == 1.0


def test_default_config_has_independent_per_axis_grid_keys():
    chart = Chart(name="Test Chart")
    assert chart.config["show_grid_x"] is True
    assert chart.config["show_grid_y"] is True
    assert "show_grid" not in chart.config


def test_default_config_has_scale_font_and_limit_keys():
    chart = Chart(name="Test Chart")
    assert chart.config["x_scale"] == "linear"
    assert chart.config["y_scale"] == "linear"
    assert chart.config["x_font_size"] == 12
    assert chart.config["y_font_size"] == 12
    assert chart.config["x_auto_limits"] is True
    assert chart.config["y_auto_limits"] is True
    assert chart.config["x_min"] == 0.0
    assert chart.config["x_max"] == 1.0


def test_default_config_has_tick_keys():
    chart = Chart(name="Test Chart")
    assert chart.config["x_tick_mode"] == "auto"
    assert chart.config["x_tick_count"] == 5
    assert chart.config["x_tick_step"] == 1.0
    assert chart.config["x_tick_format"] == "auto"
    assert chart.config["x_tick_format_custom"] == ""
    assert chart.config["y_tick_mode"] == "auto"


def test_default_config_has_legend_style_keys():
    chart = Chart(name="Test Chart")
    assert chart.config["legend_show_frame"] is True
    assert chart.config["legend_font_size"] == 10
    assert chart.config["legend_bg_color"] == "#ffffff"


def test_get_config_summary_has_grid_true_when_either_axis_enabled():
    chart = Chart(name="Test Chart")
    chart.config["show_grid_x"] = False
    chart.config["show_grid_y"] = True
    assert chart.get_config_summary()["has_grid"] is True


def test_get_config_summary_has_grid_false_when_both_axes_disabled():
    chart = Chart(name="Test Chart")
    chart.config["show_grid_x"] = False
    chart.config["show_grid_y"] = False
    assert chart.get_config_summary()["has_grid"] is False
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `pytest tests/models/test_chart_style_axes_legend_config.py -v`
Expected: FAIL — `KeyError: 'show_grid_x'` (or similar) since none of the new config keys or `DataSeries.alpha` exist yet.

- [ ] **Step 3: Add `DataSeries.alpha`**

In `pandaplot/models/project/items/chart.py`, edit the `DataSeries` dataclass:

```python
@dataclass
class DataSeries:
    """Represents a single data series in a chart."""
    dataset_id: str
    x_column: str
    y_column: str
    label: str = ""
    color: str = "#1f77b4"
    marker_color: str = ""
    marker_edge_color: str = "#000000"
    line_style: str = "solid"
    marker_style: str = "circle"
    line_width: float = 2.0
    marker_size: float = 6.0
    visible: bool = True
    alpha: float = 1.0
```

- [ ] **Step 4: Serialize `alpha` in `to_dict()` / `from_dict()`**

In `to_dict()`, inside the `data_series` list comprehension, add `"alpha": series.alpha,` after `"visible": series.visible`:

```python
            "data_series": [
                {
                    "dataset_id": series.dataset_id,
                    "x_column": series.x_column,
                    "y_column": series.y_column,
                    "label": series.label,
                    "color": series.color,
                    "marker_color": series.marker_color,
                    "marker_edge_color": series.marker_edge_color,
                    "line_style": series.line_style,
                    "marker_style": series.marker_style,
                    "line_width": series.line_width,
                    "marker_size": series.marker_size,
                    "visible": series.visible,
                    "alpha": series.alpha
                } for series in self.data_series
            ],
```

In `from_dict()`, add `alpha=series_dict.get("alpha", 1.0)` to the `DataSeries(...)` construction:

```python
            series = DataSeries(
                dataset_id=series_dict["dataset_id"],
                x_column=series_dict["x_column"],
                y_column=series_dict["y_column"],
                label=series_dict.get("label", ""),
                color=series_dict.get("color", "#1f77b4"),
                marker_color=series_dict.get("marker_color", ""),
                marker_edge_color=series_dict.get("marker_edge_color", "#000000"),
                line_style=series_dict.get("line_style", "solid"),
                marker_style=series_dict.get("marker_style", "circle"),
                line_width=series_dict.get("line_width", 2.0),
                marker_size=series_dict.get("marker_size", 6.0),
                visible=series_dict.get("visible", True),
                alpha=series_dict.get("alpha", 1.0)
            )
```

- [ ] **Step 5: Replace `_init_default_config()`**

```python
    def _init_default_config(self) -> None:
        """Initialize default chart configuration."""
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

        self.style = {
            "figure_size": (10, 6),
            "background_color": "#ffffff",
            "font_size": 12,
            "font_family": "Arial",
            "dpi": 100
        }
```

- [ ] **Step 6: Update `get_config_summary()`**

```python
    def get_config_summary(self) -> Dict[str, Any]:
        """Get a summary of the chart configuration."""
        return {
            "chart_type": self.chart_type,
            "data_series_count": len(self.data_series),
            "datasets": self.get_all_datasets(),
            "title": self.config.get("title", ""),
            "has_legend": self.config.get("show_legend", True),
            "has_grid": self.config.get("show_grid_x", True) or self.config.get("show_grid_y", True)
        }
```

- [ ] **Step 7: Run the tests to verify they pass**

Run: `pytest tests/models/test_chart_style_axes_legend_config.py -v`
Expected: PASS (9 tests).

- [ ] **Step 8: Run the full model test suite to check for regressions**

Run: `pytest tests/models -v`
Expected: PASS — in particular `tests/models/test_chart_line_style.py` must still pass unchanged.

- [ ] **Step 9: Commit**

```bash
git add pandaplot/models/project/items/chart.py tests/models/test_chart_style_axes_legend_config.py
git commit -m "Add DataSeries.alpha and per-axis grid/scale/limit/tick/legend config keys"
```

---

### Task 2: Add a testable tick-locator/formatter helper to the chart renderer

**Files:**
- Modify: `pandaplot/gui/components/tabs/chart/chart_editor.py`
- Test: `tests/gui/test_chart_editor_tick_helpers.py`

**Interfaces:**
- Consumes: nothing from Task 1.
- Produces: module-level function `apply_axis_ticks(axis, mode: str, count: int, step: float, fmt: str, custom_fmt: str) -> None` in `pandaplot/gui/components/tabs/chart/chart_editor.py`, importable as `from pandaplot.gui.components.tabs.chart.chart_editor import apply_axis_ticks`. Task 6/7 wire `chart.config`'s tick keys into this function inside `update_chart()`.

This function operates on a plain matplotlib `Axis` object (e.g. `ax.xaxis`), which can be created headlessly via `matplotlib.figure.Figure()` with no Qt/`QApplication` involved — so it can be unit tested directly, unlike the rest of `ChartEditorWidget` which requires a live Qt widget tree.

- [ ] **Step 1: Write the failing tests**

Create `tests/gui/test_chart_editor_tick_helpers.py`:

```python
"""
Unit tests for apply_axis_ticks(), the pure tick-locator/formatter helper
used by ChartEditorWidget.update_chart(). Exercised against a real
matplotlib Axis (no Qt/QApplication involved).
"""

import matplotlib
matplotlib.use("Agg")  # headless backend, no display/Qt required

from matplotlib.figure import Figure
from matplotlib.ticker import FuncFormatter, MaxNLocator, MultipleLocator

from pandaplot.gui.components.tabs.chart.chart_editor import apply_axis_ticks


def _make_axis():
    fig = Figure()
    ax = fig.add_subplot(111)
    return ax.xaxis


def test_auto_mode_leaves_default_locator_untouched():
    axis = _make_axis()
    default_locator = axis.get_major_locator()
    apply_axis_ticks(axis, "auto", count=5, step=1.0, fmt="auto", custom_fmt="")
    assert axis.get_major_locator() is default_locator


def test_count_mode_sets_max_n_locator():
    axis = _make_axis()
    apply_axis_ticks(axis, "count", count=8, step=1.0, fmt="auto", custom_fmt="")
    locator = axis.get_major_locator()
    assert isinstance(locator, MaxNLocator)


def test_step_mode_sets_multiple_locator():
    axis = _make_axis()
    apply_axis_ticks(axis, "step", count=5, step=2.5, fmt="auto", custom_fmt="")
    locator = axis.get_major_locator()
    assert isinstance(locator, MultipleLocator)


def test_integer_format_renders_whole_numbers():
    axis = _make_axis()
    apply_axis_ticks(axis, "auto", count=5, step=1.0, fmt="integer", custom_fmt="")
    formatter = axis.get_major_formatter()
    assert isinstance(formatter, FuncFormatter)
    assert formatter(3.7, 0) == "4"


def test_two_decimal_format():
    axis = _make_axis()
    apply_axis_ticks(axis, "auto", count=5, step=1.0, fmt="2decimal", custom_fmt="")
    formatter = axis.get_major_formatter()
    assert formatter(3.14159, 0) == "3.14"


def test_scientific_format():
    axis = _make_axis()
    apply_axis_ticks(axis, "auto", count=5, step=1.0, fmt="scientific", custom_fmt="")
    formatter = axis.get_major_formatter()
    assert formatter(1234.5, 0) == "1.23e+03"


def test_valid_custom_format_is_applied():
    axis = _make_axis()
    apply_axis_ticks(axis, "auto", count=5, step=1.0, fmt="custom", custom_fmt="{:.1f}kg")
    formatter = axis.get_major_formatter()
    assert formatter(2.0, 0) == "2.0kg"


def test_invalid_custom_format_falls_back_to_plain_number_instead_of_raising():
    axis = _make_axis()
    apply_axis_ticks(axis, "auto", count=5, step=1.0, fmt="custom", custom_fmt="{:z}")
    formatter = axis.get_major_formatter()
    assert formatter(2.0, 0) == "2.0"
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `pytest tests/gui/test_chart_editor_tick_helpers.py -v`
Expected: FAIL — `ImportError: cannot import name 'apply_axis_ticks'`.

- [ ] **Step 3: Implement `apply_axis_ticks`**

In `pandaplot/gui/components/tabs/chart/chart_editor.py`, add the import and function after the existing imports (before the `class ChartEditorWidget:` line):

```python
from matplotlib.ticker import FuncFormatter, MaxNLocator, MultipleLocator
```

```python
def apply_axis_ticks(axis, mode, count, step, fmt, custom_fmt):
    """Apply tick placement and label formatting to a matplotlib Axis.

    axis: a matplotlib Axis object (e.g. ax.xaxis or ax.yaxis)
    mode: "auto" | "count" | "step" - tick placement strategy
    count: number of ticks when mode == "count"
    step: fixed spacing between ticks when mode == "step"
    fmt: "auto" | "integer" | "1decimal" | "2decimal" | "scientific" | "custom"
    custom_fmt: a Python format spec (e.g. "{:.2f}") used when fmt == "custom"
    """
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
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `pytest tests/gui/test_chart_editor_tick_helpers.py -v`
Expected: PASS (8 tests).

- [ ] **Step 5: Commit**

```bash
git add pandaplot/gui/components/tabs/chart/chart_editor.py tests/gui/test_chart_editor_tick_helpers.py
git commit -m "Add apply_axis_ticks helper for tick locator/formatter configuration"
```

---

### Task 3: Fix "Show Grid" to be truly independent per axis

**Files:**
- Modify: `pandaplot/gui/components/sidebar/chart/chart_properties_panel.py`
- Modify: `pandaplot/gui/components/tabs/chart/chart_editor.py`

**Interfaces:**
- Consumes: `chart.config["show_grid_x"]` / `["show_grid_y"]` from Task 1.
- Produces: no new interfaces; this task closes out the bug reported in the spec.

This task has no automated test (it's pure Qt signal-wiring + a single rendering call change, and this repo has no Qt widget test infrastructure — see Global Constraints). Verify with the exact manual steps in Step 5.

- [ ] **Step 1: Fix the write side in `_on_chart_config_changed`**

In `pandaplot/gui/components/sidebar/chart/chart_properties_panel.py`, replace:

```python
        if hasattr(self, "x_grid_check") and hasattr(self, "y_grid_check"):
            config["show_grid"] = self.x_grid_check.isChecked() and self.y_grid_check.isChecked()
```

with:

```python
        if hasattr(self, "x_grid_check"):
            config["show_grid_x"] = self.x_grid_check.isChecked()
        if hasattr(self, "y_grid_check"):
            config["show_grid_y"] = self.y_grid_check.isChecked()
```

- [ ] **Step 2: Fix the write side in `apply_to_chart`**

Replace:

```python
        chart.config["show_grid"] = self.x_grid_check.isChecked() and self.y_grid_check.isChecked()
```

with:

```python
        chart.config["show_grid_x"] = self.x_grid_check.isChecked()
        chart.config["show_grid_y"] = self.y_grid_check.isChecked()
```

- [ ] **Step 3: Fix the read side in `load_chart_object`**

Replace:

```python
            self.x_grid_check.setChecked(config.get("show_grid", True))
            self.y_grid_check.setChecked(config.get("show_grid", True))
```

with:

```python
            self.x_grid_check.setChecked(config.get("show_grid_x", True))
            self.y_grid_check.setChecked(config.get("show_grid_y", True))
```

- [ ] **Step 4: Make the renderer apply grid independently per axis**

In `pandaplot/gui/components/tabs/chart/chart_editor.py`, replace:

```python
            if config.get("show_grid", True):
                self.chart_canvas.axes.grid(
                    True, alpha=config.get("grid_alpha", 0.3))
```

with:

```python
            self.chart_canvas.axes.grid(
                config.get("show_grid_x", True), axis="x", alpha=config.get("grid_alpha", 0.3))
            self.chart_canvas.axes.grid(
                config.get("show_grid_y", True), axis="y", alpha=config.get("grid_alpha", 0.3))
```

- [ ] **Step 5: Manually verify in the running app**

Run: `python -m pandaplot` (or the project's normal launch command)

1. Create or open a chart with at least one data series.
2. Open the chart properties sidebar, go to the Axes tab.
3. Uncheck "Show Grid" under X Axis only, leave Y Axis checked. Click Apply. Confirm vertical gridlines disappear while horizontal gridlines remain.
4. Re-check X, uncheck Y instead. Click Apply. Confirm horizontal gridlines disappear while vertical gridlines remain.
5. Uncheck both. Confirm no gridlines. Re-check both. Confirm both reappear.
6. Save the project, close and reopen the chart. Confirm the X/Y grid checkboxes reflect the last-saved state independently (not coupled).

- [ ] **Step 6: Commit**

```bash
git add pandaplot/gui/components/sidebar/chart/chart_properties_panel.py pandaplot/gui/components/tabs/chart/chart_editor.py
git commit -m "Fix Show Grid checkboxes to control X/Y gridlines independently"
```

---

### Task 4: Wire Line Transparency end-to-end

**Files:**
- Modify: `pandaplot/gui/components/sidebar/chart/chart_properties_panel.py`
- Modify: `pandaplot/gui/components/tabs/chart/chart_editor.py`

**Interfaces:**
- Consumes: `DataSeries.alpha` from Task 1.
- Produces: no new interfaces.

No automated test (Qt wiring only — see Global Constraints). Verify with Step 5.

- [ ] **Step 1: Write the value in `_on_style_changed`**

In `pandaplot/gui/components/sidebar/chart/chart_properties_panel.py`, in the data-series branch of `_on_style_changed` (alongside `series.line_width = ...` / `series.marker_size = ...`), add:

```python
            series.line_width = self.line_width_spin.value()
            series.marker_size = self.marker_size_spin.value()
            series.alpha = self.line_transparency_spin.value()
```

- [ ] **Step 2: Write the value in `apply_to_chart`**

In the data-series branch of `apply_to_chart` (alongside `series.line_width = ...` / `series.marker_size = ...`), add:

```python
                series.line_width = self.line_width_spin.value()
                series.marker_size = self.marker_size_spin.value()
                series.alpha = self.line_transparency_spin.value()
```

- [ ] **Step 3: Load the value in `_load_series_into_controls`**

In `_load_series_into_controls`, alongside the existing `marker_size_spin` block-signals pattern:

```python
            self.marker_size_spin.blockSignals(True)
            self.marker_size_spin.setValue(series.marker_size)
            self.marker_size_spin.blockSignals(False)

            self.line_transparency_spin.blockSignals(True)
            self.line_transparency_spin.setValue(series.alpha)
            self.line_transparency_spin.blockSignals(False)
```

- [ ] **Step 4: Apply `alpha` in the renderer**

In `pandaplot/gui/components/tabs/chart/chart_editor.py`, replace every hardcoded transparency expression in the four chart-type branches of `update_chart()`'s main plotting loop:

Line-chart branch: replace `alpha=1.0 if series.visible else 0.3` with `alpha=series.alpha if series.visible else 0.3`.

Scatter branch: replace `alpha=1.0 if series.visible else 0.3` with `alpha=series.alpha if series.visible else 0.3`.

Bar branch: replace `alpha=1.0 if series.visible else 0.3` with `alpha=series.alpha if series.visible else 0.3`.

Histogram branch: replace `alpha=0.7 if series.visible else 0.3` with `alpha=series.alpha if series.visible else 0.3`.

Leave the two fallback branches ("Column not found" at `alpha=0.5`, "Dataset not found" at `alpha=0.5`) unchanged — those are error-state renders for a different series than the one being edited, out of scope.

- [ ] **Step 5: Manually verify in the running app**

Run: `python -m pandaplot`

1. Open a chart with a line or scatter series. In the Style tab, set Transparency to 0.3 and Apply. Confirm the series renders visibly faded/transparent.
2. Set Transparency back to 1.0 and Apply. Confirm it renders fully opaque again.
3. Toggle the series' Visible checkbox off (existing feature). Confirm it still dims to the pre-existing "hidden" look (0.3 alpha) regardless of the Transparency spinbox value — the two behaviors don't conflict.
4. Save and reopen the project; confirm the Transparency spinbox shows the last-saved value for that series when re-selected in the series list.

- [ ] **Step 6: Commit**

```bash
git add pandaplot/gui/components/sidebar/chart/chart_properties_panel.py pandaplot/gui/components/tabs/chart/chart_editor.py
git commit -m "Wire Line Transparency control to DataSeries.alpha and chart rendering"
```

---

### Task 5: Wire Axes Font Size and Scale end-to-end

**Files:**
- Modify: `pandaplot/gui/components/sidebar/chart/chart_properties_panel.py`
- Modify: `pandaplot/gui/components/tabs/chart/chart_editor.py`

**Interfaces:**
- Consumes: `chart.config["x_font_size"]`/`["y_font_size"]`/`["x_scale"]`/`["y_scale"]` from Task 1.
- Produces: no new interfaces.

No automated test (Qt wiring only). Verify with Step 6.

- [ ] **Step 1: Connect the signals**

In `_connect_signals`, alongside the existing `x_grid_check`/`y_grid_check` connections:

```python
        self.x_grid_check.toggled.connect(self._on_chart_config_changed)
        self.y_grid_check.toggled.connect(self._on_chart_config_changed)
        self.x_font_size_spin.valueChanged.connect(self._on_chart_config_changed)
        self.x_scale_combo.currentIndexChanged.connect(self._on_chart_config_changed)
        self.y_font_size_spin.valueChanged.connect(self._on_chart_config_changed)
        self.y_scale_combo.currentIndexChanged.connect(self._on_chart_config_changed)
```

- [ ] **Step 2: Write the values in `_on_chart_config_changed`**

Alongside the grid writes from Task 3:

```python
        if hasattr(self, "x_font_size_spin"):
            config["x_font_size"] = self.x_font_size_spin.value()
        if hasattr(self, "y_font_size_spin"):
            config["y_font_size"] = self.y_font_size_spin.value()
        if hasattr(self, "x_scale_combo") and self.x_scale_combo.currentData():
            config["x_scale"] = self.x_scale_combo.currentData().value
        if hasattr(self, "y_scale_combo") and self.y_scale_combo.currentData():
            config["y_scale"] = self.y_scale_combo.currentData().value
```

- [ ] **Step 3: Write the values in `apply_to_chart`**

```python
        chart.config["x_font_size"] = self.x_font_size_spin.value()
        chart.config["y_font_size"] = self.y_font_size_spin.value()
        if self.x_scale_combo.currentData():
            chart.config["x_scale"] = self.x_scale_combo.currentData().value
        if self.y_scale_combo.currentData():
            chart.config["y_scale"] = self.y_scale_combo.currentData().value
```

- [ ] **Step 4: Load the values in `load_chart_object`**

Alongside the grid-loading lines from Task 3:

```python
            self.x_font_size_spin.setValue(config.get("x_font_size", 12))
            self.y_font_size_spin.setValue(config.get("y_font_size", 12))
            x_scale_value = config.get("x_scale", "linear")
            for i in range(self.x_scale_combo.count()):
                if self.x_scale_combo.itemData(i) and self.x_scale_combo.itemData(i).value == x_scale_value:
                    self.x_scale_combo.setCurrentIndex(i)
                    break
            y_scale_value = config.get("y_scale", "linear")
            for i in range(self.y_scale_combo.count()):
                if self.y_scale_combo.itemData(i) and self.y_scale_combo.itemData(i).value == y_scale_value:
                    self.y_scale_combo.setCurrentIndex(i)
                    break
```

- [ ] **Step 5: Apply font size and scale in the renderer**

In `pandaplot/gui/components/tabs/chart/chart_editor.py`, immediately after the existing:

```python
            self.chart_canvas.axes.set_xlabel(config.get("x_label", ""))
            self.chart_canvas.axes.set_ylabel(config.get("y_label", ""))
```

add:

```python
            self.chart_canvas.axes.set_xscale(config.get("x_scale", "linear"))
            self.chart_canvas.axes.set_yscale(config.get("y_scale", "linear"))
            self.chart_canvas.axes.xaxis.label.set_size(config.get("x_font_size", 12))
            self.chart_canvas.axes.yaxis.label.set_size(config.get("y_font_size", 12))
```

- [ ] **Step 6: Manually verify in the running app**

Run: `python -m pandaplot`

1. Open a chart with numeric, strictly-positive data on both axes. In the Axes tab, set X Font Size to 20 and Apply. Confirm the X axis label text visibly grows.
2. Set X Scale to "Log" and Apply. Confirm the X axis renders log-scaled (nonlinear tick spacing).
3. Set X Scale back to "Linear" and Apply. Confirm it returns to normal.
4. Repeat for Y Font Size / Y Scale.
5. Save and reopen the project; confirm Font Size and Scale values persist.

- [ ] **Step 7: Commit**

```bash
git add pandaplot/gui/components/sidebar/chart/chart_properties_panel.py pandaplot/gui/components/tabs/chart/chart_editor.py
git commit -m "Wire Axes Font Size and Scale controls to chart rendering"
```

---

### Task 6: Add X/Y axis limit controls (Auto + Min/Max)

**Files:**
- Modify: `pandaplot/gui/components/sidebar/chart/chart_properties_panel.py`
- Modify: `pandaplot/gui/components/tabs/chart/chart_editor.py`

**Interfaces:**
- Consumes: `chart.config["x_auto_limits"]`/`["x_min"]`/`["x_max"]`/`["y_auto_limits"]`/`["y_min"]`/`["y_max"]` from Task 1.
- Produces: new widgets `x_auto_limits_check`, `x_min_spin`, `x_max_spin`, `y_auto_limits_check`, `y_min_spin`, `y_max_spin` on `ChartPropertiesPanel`, consumed only within this task.

No automated test (Qt wiring only). Verify with Step 6.

- [ ] **Step 1: Add the Limits widgets to the X Axis group**

In `_create_axes_tab`, insert after the X Scale row (`x_axis_layout.addWidget(self.x_scale_combo, 2, 1)`) and before the existing `x_grid_check` row:

```python
        x_axis_layout.addWidget(QLabel("Limits:"), 3, 0)
        self.x_auto_limits_check = QCheckBox("Auto")
        self.x_auto_limits_check.setChecked(True)
        x_axis_layout.addWidget(self.x_auto_limits_check, 3, 1)

        x_axis_layout.addWidget(QLabel("Min:"), 4, 0)
        self.x_min_spin = QDoubleSpinBox()
        self.x_min_spin.setRange(-1e9, 1e9)
        self.x_min_spin.setValue(0.0)
        self.x_min_spin.setEnabled(False)
        x_axis_layout.addWidget(self.x_min_spin, 4, 1)

        x_axis_layout.addWidget(QLabel("Max:"), 5, 0)
        self.x_max_spin = QDoubleSpinBox()
        self.x_max_spin.setRange(-1e9, 1e9)
        self.x_max_spin.setValue(1.0)
        self.x_max_spin.setEnabled(False)
        x_axis_layout.addWidget(self.x_max_spin, 5, 1)
```

Renumber the existing `x_grid_check` row from `3` to `6`:

```python
        self.x_grid_check = QCheckBox("Show Grid")
        self.x_grid_check.setChecked(True)
        x_axis_layout.addWidget(self.x_grid_check, 6, 0, 1, 2)
```

- [ ] **Step 2: Add the same widgets to the Y Axis group**

Mirror Step 1 in the Y Axis group (after `y_scale_combo`, before `y_grid_check`, renumbering `y_grid_check`'s row from `3` to `6`):

```python
        y_axis_layout.addWidget(QLabel("Limits:"), 3, 0)
        self.y_auto_limits_check = QCheckBox("Auto")
        self.y_auto_limits_check.setChecked(True)
        y_axis_layout.addWidget(self.y_auto_limits_check, 3, 1)

        y_axis_layout.addWidget(QLabel("Min:"), 4, 0)
        self.y_min_spin = QDoubleSpinBox()
        self.y_min_spin.setRange(-1e9, 1e9)
        self.y_min_spin.setValue(0.0)
        self.y_min_spin.setEnabled(False)
        y_axis_layout.addWidget(self.y_min_spin, 4, 1)

        y_axis_layout.addWidget(QLabel("Max:"), 5, 0)
        self.y_max_spin = QDoubleSpinBox()
        self.y_max_spin.setRange(-1e9, 1e9)
        self.y_max_spin.setValue(1.0)
        self.y_max_spin.setEnabled(False)
        y_axis_layout.addWidget(self.y_max_spin, 5, 1)
```

```python
        self.y_grid_check = QCheckBox("Show Grid")
        self.y_grid_check.setChecked(True)
        y_axis_layout.addWidget(self.y_grid_check, 6, 0, 1, 2)
```

- [ ] **Step 3: Add toggle handlers and connect signals**

Add two new methods near `_on_chart_config_changed`:

```python
    def _on_x_auto_limits_toggled(self, checked):
        self.x_min_spin.setEnabled(not checked)
        self.x_max_spin.setEnabled(not checked)
        self._on_chart_config_changed()

    def _on_y_auto_limits_toggled(self, checked):
        self.y_min_spin.setEnabled(not checked)
        self.y_max_spin.setEnabled(not checked)
        self._on_chart_config_changed()
```

In `_connect_signals`, add:

```python
        self.x_auto_limits_check.toggled.connect(self._on_x_auto_limits_toggled)
        self.x_min_spin.valueChanged.connect(self._on_chart_config_changed)
        self.x_max_spin.valueChanged.connect(self._on_chart_config_changed)
        self.y_auto_limits_check.toggled.connect(self._on_y_auto_limits_toggled)
        self.y_min_spin.valueChanged.connect(self._on_chart_config_changed)
        self.y_max_spin.valueChanged.connect(self._on_chart_config_changed)
```

- [ ] **Step 4: Write the values in `_on_chart_config_changed` and `apply_to_chart`**

In `_on_chart_config_changed`:

```python
        if hasattr(self, "x_auto_limits_check"):
            config["x_auto_limits"] = self.x_auto_limits_check.isChecked()
            config["x_min"] = self.x_min_spin.value()
            config["x_max"] = self.x_max_spin.value()
        if hasattr(self, "y_auto_limits_check"):
            config["y_auto_limits"] = self.y_auto_limits_check.isChecked()
            config["y_min"] = self.y_min_spin.value()
            config["y_max"] = self.y_max_spin.value()
```

In `apply_to_chart`:

```python
        chart.config["x_auto_limits"] = self.x_auto_limits_check.isChecked()
        chart.config["x_min"] = self.x_min_spin.value()
        chart.config["x_max"] = self.x_max_spin.value()
        chart.config["y_auto_limits"] = self.y_auto_limits_check.isChecked()
        chart.config["y_min"] = self.y_min_spin.value()
        chart.config["y_max"] = self.y_max_spin.value()
```

- [ ] **Step 5: Load the values in `load_chart_object`**

```python
            self.x_auto_limits_check.setChecked(config.get("x_auto_limits", True))
            self.x_min_spin.setValue(config.get("x_min", 0.0))
            self.x_max_spin.setValue(config.get("x_max", 1.0))
            self.x_min_spin.setEnabled(not self.x_auto_limits_check.isChecked())
            self.x_max_spin.setEnabled(not self.x_auto_limits_check.isChecked())

            self.y_auto_limits_check.setChecked(config.get("y_auto_limits", True))
            self.y_min_spin.setValue(config.get("y_min", 0.0))
            self.y_max_spin.setValue(config.get("y_max", 1.0))
            self.y_min_spin.setEnabled(not self.y_auto_limits_check.isChecked())
            self.y_max_spin.setEnabled(not self.y_auto_limits_check.isChecked())
```

- [ ] **Step 6: Apply limits in the renderer**

In `pandaplot/gui/components/tabs/chart/chart_editor.py`, after the font-size block added in Task 5:

```python
            if not config.get("x_auto_limits", True):
                self.chart_canvas.axes.set_xlim(config.get("x_min", 0.0), config.get("x_max", 1.0))
            if not config.get("y_auto_limits", True):
                self.chart_canvas.axes.set_ylim(config.get("y_min", 0.0), config.get("y_max", 1.0))
```

- [ ] **Step 7: Manually verify in the running app**

Run: `python -m pandaplot`

1. Open a chart with data. In the Axes tab, uncheck X "Auto" under Limits. Confirm the Min/Max spinboxes become enabled.
2. Set X Min/Max to a narrower range than the data's natural extent and Apply. Confirm the chart's X axis is clamped to that range (data outside it is clipped from view).
3. Re-check X "Auto". Confirm Min/Max spinboxes grey out again and the X axis returns to autoscaled.
4. Repeat for Y.
5. Use the chart's "reset zoom" toolbar button while manual limits are active; confirm it returns to the configured min/max (not to the full data extent).
6. Save and reopen the project; confirm the Auto checkbox and Min/Max values persist.

- [ ] **Step 8: Commit**

```bash
git add pandaplot/gui/components/sidebar/chart/chart_properties_panel.py pandaplot/gui/components/tabs/chart/chart_editor.py
git commit -m "Add X/Y axis limit controls (auto-scale or manual min/max)"
```

---

### Task 7: Add X/Y tick mode and format controls

**Files:**
- Modify: `pandaplot/gui/components/sidebar/chart/chart_properties_panel.py`
- Modify: `pandaplot/gui/components/tabs/chart/chart_editor.py`

**Interfaces:**
- Consumes: `apply_axis_ticks()` from Task 2; `chart.config`'s `x_tick_*`/`y_tick_*` keys from Task 1.
- Produces: new widgets `x_tick_mode_combo`, `x_tick_count_spin`, `x_tick_step_spin`, `x_tick_format_combo`, `x_tick_format_custom_edit` (and `y_*` equivalents), consumed only within this task.

No automated test for the Qt wiring (see Global Constraints) — the underlying tick logic itself is already covered by Task 2's tests. Verify wiring with Step 7.

- [ ] **Step 1: Add the Ticks widgets to the X Axis group**

In `_create_axes_tab`, insert after the Limits rows added in Task 6 (rows 3-5) and before the renumbered `x_grid_check` row, then renumber `x_grid_check` from row `6` to row `11`:

```python
        x_axis_layout.addWidget(QLabel("Tick Mode:"), 6, 0)
        self.x_tick_mode_combo = QComboBox()
        self.x_tick_mode_combo.addItem("Auto", "auto")
        self.x_tick_mode_combo.addItem("Fixed Count", "count")
        self.x_tick_mode_combo.addItem("Fixed Step", "step")
        x_axis_layout.addWidget(self.x_tick_mode_combo, 6, 1)

        x_axis_layout.addWidget(QLabel("Tick Count:"), 7, 0)
        self.x_tick_count_spin = QSpinBox()
        self.x_tick_count_spin.setRange(2, 50)
        self.x_tick_count_spin.setValue(5)
        self.x_tick_count_spin.setEnabled(False)
        x_axis_layout.addWidget(self.x_tick_count_spin, 7, 1)

        x_axis_layout.addWidget(QLabel("Tick Step:"), 8, 0)
        self.x_tick_step_spin = QDoubleSpinBox()
        self.x_tick_step_spin.setRange(0.001, 1e9)
        self.x_tick_step_spin.setValue(1.0)
        self.x_tick_step_spin.setEnabled(False)
        x_axis_layout.addWidget(self.x_tick_step_spin, 8, 1)

        x_axis_layout.addWidget(QLabel("Tick Format:"), 9, 0)
        self.x_tick_format_combo = QComboBox()
        self.x_tick_format_combo.addItem("Auto", "auto")
        self.x_tick_format_combo.addItem("Integer", "integer")
        self.x_tick_format_combo.addItem("1 Decimal", "1decimal")
        self.x_tick_format_combo.addItem("2 Decimals", "2decimal")
        self.x_tick_format_combo.addItem("Scientific", "scientific")
        self.x_tick_format_combo.addItem("Custom...", "custom")
        x_axis_layout.addWidget(self.x_tick_format_combo, 9, 1)

        x_axis_layout.addWidget(QLabel("Custom Format:"), 10, 0)
        self.x_tick_format_custom_edit = QLineEdit()
        self.x_tick_format_custom_edit.setPlaceholderText("e.g. {:.2f} units")
        self.x_tick_format_custom_edit.setEnabled(False)
        x_axis_layout.addWidget(self.x_tick_format_custom_edit, 10, 1)
```

```python
        self.x_grid_check = QCheckBox("Show Grid")
        self.x_grid_check.setChecked(True)
        x_axis_layout.addWidget(self.x_grid_check, 11, 0, 1, 2)
```

- [ ] **Step 2: Mirror the Ticks widgets in the Y Axis group**

Same as Step 1 with `y_` prefixes, inserted after Task 6's Y Limits rows (3-5), and renumber `y_grid_check` from row `6` to row `11`:

```python
        y_axis_layout.addWidget(QLabel("Tick Mode:"), 6, 0)
        self.y_tick_mode_combo = QComboBox()
        self.y_tick_mode_combo.addItem("Auto", "auto")
        self.y_tick_mode_combo.addItem("Fixed Count", "count")
        self.y_tick_mode_combo.addItem("Fixed Step", "step")
        y_axis_layout.addWidget(self.y_tick_mode_combo, 6, 1)

        y_axis_layout.addWidget(QLabel("Tick Count:"), 7, 0)
        self.y_tick_count_spin = QSpinBox()
        self.y_tick_count_spin.setRange(2, 50)
        self.y_tick_count_spin.setValue(5)
        self.y_tick_count_spin.setEnabled(False)
        y_axis_layout.addWidget(self.y_tick_count_spin, 7, 1)

        y_axis_layout.addWidget(QLabel("Tick Step:"), 8, 0)
        self.y_tick_step_spin = QDoubleSpinBox()
        self.y_tick_step_spin.setRange(0.001, 1e9)
        self.y_tick_step_spin.setValue(1.0)
        self.y_tick_step_spin.setEnabled(False)
        y_axis_layout.addWidget(self.y_tick_step_spin, 8, 1)

        y_axis_layout.addWidget(QLabel("Tick Format:"), 9, 0)
        self.y_tick_format_combo = QComboBox()
        self.y_tick_format_combo.addItem("Auto", "auto")
        self.y_tick_format_combo.addItem("Integer", "integer")
        self.y_tick_format_combo.addItem("1 Decimal", "1decimal")
        self.y_tick_format_combo.addItem("2 Decimals", "2decimal")
        self.y_tick_format_combo.addItem("Scientific", "scientific")
        self.y_tick_format_combo.addItem("Custom...", "custom")
        y_axis_layout.addWidget(self.y_tick_format_combo, 9, 1)

        y_axis_layout.addWidget(QLabel("Custom Format:"), 10, 0)
        self.y_tick_format_custom_edit = QLineEdit()
        self.y_tick_format_custom_edit.setPlaceholderText("e.g. {:.2f} units")
        self.y_tick_format_custom_edit.setEnabled(False)
        y_axis_layout.addWidget(self.y_tick_format_custom_edit, 10, 1)
```

```python
        self.y_grid_check = QCheckBox("Show Grid")
        self.y_grid_check.setChecked(True)
        y_axis_layout.addWidget(self.y_grid_check, 11, 0, 1, 2)
```

- [ ] **Step 3: Add enable/disable handlers and connect signals**

Add near `_on_x_auto_limits_toggled`:

```python
    def _on_x_tick_mode_changed(self):
        mode = self.x_tick_mode_combo.currentData()
        self.x_tick_count_spin.setEnabled(mode == "count")
        self.x_tick_step_spin.setEnabled(mode == "step")
        self._on_chart_config_changed()

    def _on_x_tick_format_changed(self):
        self.x_tick_format_custom_edit.setEnabled(self.x_tick_format_combo.currentData() == "custom")
        self._on_chart_config_changed()

    def _on_y_tick_mode_changed(self):
        mode = self.y_tick_mode_combo.currentData()
        self.y_tick_count_spin.setEnabled(mode == "count")
        self.y_tick_step_spin.setEnabled(mode == "step")
        self._on_chart_config_changed()

    def _on_y_tick_format_changed(self):
        self.y_tick_format_custom_edit.setEnabled(self.y_tick_format_combo.currentData() == "custom")
        self._on_chart_config_changed()
```

In `_connect_signals`, add:

```python
        self.x_tick_mode_combo.currentIndexChanged.connect(self._on_x_tick_mode_changed)
        self.x_tick_count_spin.valueChanged.connect(self._on_chart_config_changed)
        self.x_tick_step_spin.valueChanged.connect(self._on_chart_config_changed)
        self.x_tick_format_combo.currentIndexChanged.connect(self._on_x_tick_format_changed)
        self.x_tick_format_custom_edit.textChanged.connect(self._on_chart_config_changed)
        self.y_tick_mode_combo.currentIndexChanged.connect(self._on_y_tick_mode_changed)
        self.y_tick_count_spin.valueChanged.connect(self._on_chart_config_changed)
        self.y_tick_step_spin.valueChanged.connect(self._on_chart_config_changed)
        self.y_tick_format_combo.currentIndexChanged.connect(self._on_y_tick_format_changed)
        self.y_tick_format_custom_edit.textChanged.connect(self._on_chart_config_changed)
```

- [ ] **Step 4: Write the values in `_on_chart_config_changed` and `apply_to_chart`**

In `_on_chart_config_changed`:

```python
        if hasattr(self, "x_tick_mode_combo"):
            config["x_tick_mode"] = self.x_tick_mode_combo.currentData()
            config["x_tick_count"] = self.x_tick_count_spin.value()
            config["x_tick_step"] = self.x_tick_step_spin.value()
            config["x_tick_format"] = self.x_tick_format_combo.currentData()
            config["x_tick_format_custom"] = self.x_tick_format_custom_edit.text()
        if hasattr(self, "y_tick_mode_combo"):
            config["y_tick_mode"] = self.y_tick_mode_combo.currentData()
            config["y_tick_count"] = self.y_tick_count_spin.value()
            config["y_tick_step"] = self.y_tick_step_spin.value()
            config["y_tick_format"] = self.y_tick_format_combo.currentData()
            config["y_tick_format_custom"] = self.y_tick_format_custom_edit.text()
```

In `apply_to_chart`:

```python
        chart.config["x_tick_mode"] = self.x_tick_mode_combo.currentData()
        chart.config["x_tick_count"] = self.x_tick_count_spin.value()
        chart.config["x_tick_step"] = self.x_tick_step_spin.value()
        chart.config["x_tick_format"] = self.x_tick_format_combo.currentData()
        chart.config["x_tick_format_custom"] = self.x_tick_format_custom_edit.text()
        chart.config["y_tick_mode"] = self.y_tick_mode_combo.currentData()
        chart.config["y_tick_count"] = self.y_tick_count_spin.value()
        chart.config["y_tick_step"] = self.y_tick_step_spin.value()
        chart.config["y_tick_format"] = self.y_tick_format_combo.currentData()
        chart.config["y_tick_format_custom"] = self.y_tick_format_custom_edit.text()
```

- [ ] **Step 5: Load the values in `load_chart_object`**

```python
            x_tick_mode = config.get("x_tick_mode", "auto")
            for i in range(self.x_tick_mode_combo.count()):
                if self.x_tick_mode_combo.itemData(i) == x_tick_mode:
                    self.x_tick_mode_combo.setCurrentIndex(i)
                    break
            self.x_tick_count_spin.setValue(config.get("x_tick_count", 5))
            self.x_tick_step_spin.setValue(config.get("x_tick_step", 1.0))
            self.x_tick_count_spin.setEnabled(x_tick_mode == "count")
            self.x_tick_step_spin.setEnabled(x_tick_mode == "step")

            x_tick_format = config.get("x_tick_format", "auto")
            for i in range(self.x_tick_format_combo.count()):
                if self.x_tick_format_combo.itemData(i) == x_tick_format:
                    self.x_tick_format_combo.setCurrentIndex(i)
                    break
            self.x_tick_format_custom_edit.setText(config.get("x_tick_format_custom", ""))
            self.x_tick_format_custom_edit.setEnabled(x_tick_format == "custom")

            y_tick_mode = config.get("y_tick_mode", "auto")
            for i in range(self.y_tick_mode_combo.count()):
                if self.y_tick_mode_combo.itemData(i) == y_tick_mode:
                    self.y_tick_mode_combo.setCurrentIndex(i)
                    break
            self.y_tick_count_spin.setValue(config.get("y_tick_count", 5))
            self.y_tick_step_spin.setValue(config.get("y_tick_step", 1.0))
            self.y_tick_count_spin.setEnabled(y_tick_mode == "count")
            self.y_tick_step_spin.setEnabled(y_tick_mode == "step")

            y_tick_format = config.get("y_tick_format", "auto")
            for i in range(self.y_tick_format_combo.count()):
                if self.y_tick_format_combo.itemData(i) == y_tick_format:
                    self.y_tick_format_combo.setCurrentIndex(i)
                    break
            self.y_tick_format_custom_edit.setText(config.get("y_tick_format_custom", ""))
            self.y_tick_format_custom_edit.setEnabled(y_tick_format == "custom")
```

- [ ] **Step 6: Apply ticks in the renderer using `apply_axis_ticks`**

In `pandaplot/gui/components/tabs/chart/chart_editor.py`, after the limits block added in Task 6:

```python
            apply_axis_ticks(
                self.chart_canvas.axes.xaxis,
                config.get("x_tick_mode", "auto"), config.get("x_tick_count", 5),
                config.get("x_tick_step", 1.0), config.get("x_tick_format", "auto"),
                config.get("x_tick_format_custom", ""))
            apply_axis_ticks(
                self.chart_canvas.axes.yaxis,
                config.get("y_tick_mode", "auto"), config.get("y_tick_count", 5),
                config.get("y_tick_step", 1.0), config.get("y_tick_format", "auto"),
                config.get("y_tick_format_custom", ""))
```

- [ ] **Step 7: Manually verify in the running app**

Run: `python -m pandaplot`

1. Open a chart with data. In the Axes tab, set X Tick Mode to "Fixed Count" with count 10 and Apply. Confirm the X axis shows roughly 10 ticks. Confirm the Tick Count spinbox is enabled and Tick Step is disabled.
2. Set X Tick Mode to "Fixed Step" with step 0.5 and Apply. Confirm ticks are spaced 0.5 apart. Confirm Tick Step is enabled and Tick Count is disabled.
3. Set X Tick Mode back to "Auto" and Apply. Confirm ticks return to matplotlib's default placement.
4. Set X Tick Format to "2 Decimals" and Apply. Confirm tick labels show two decimal places.
5. Set X Tick Format to "Custom..." with format `"{:.1f}kg"` and Apply. Confirm tick labels render like `"2.0kg"`. Confirm the Custom Format field is only enabled when "Custom..." is selected.
6. Set the custom format to an invalid spec like `"{:z}"` and Apply. Confirm the chart still renders (tick labels fall back to plain numbers) rather than crashing.
7. Repeat 1-6 for the Y axis.
8. Save and reopen the project; confirm all tick settings persist.

- [ ] **Step 8: Commit**

```bash
git add pandaplot/gui/components/sidebar/chart/chart_properties_panel.py pandaplot/gui/components/tabs/chart/chart_editor.py
git commit -m "Add X/Y tick mode and format controls wired to apply_axis_ticks"
```

---

### Task 8: Wire Legend Position/Font Size/Background and add a Show Frame toggle

**Files:**
- Modify: `pandaplot/gui/components/sidebar/chart/chart_properties_panel.py`
- Modify: `pandaplot/gui/components/tabs/chart/chart_editor.py`

**Interfaces:**
- Consumes: `chart.config["legend_position"]`/`["legend_font_size"]`/`["legend_bg_color"]`/`["legend_show_frame"]` from Task 1.
- Produces: new widget `legend_show_frame_check` on `ChartPropertiesPanel`.

No automated test (Qt wiring only). Verify with Step 6.

- [ ] **Step 1: Add the Show Frame checkbox**

In `_create_legend_tab`, after the Background row:

```python
        legend_layout.addWidget(QLabel("Background:"), 3, 0)
        self.legend_bg_color_button = ColorButton(self.app_context, None, "#ffffff")
        legend_layout.addWidget(self.legend_bg_color_button, 3, 1)

        self.legend_show_frame_check = QCheckBox("Show Frame")
        self.legend_show_frame_check.setChecked(True)
        legend_layout.addWidget(self.legend_show_frame_check, 4, 0, 1, 2)
```

- [ ] **Step 2: Connect the signals**

In `_connect_signals`, alongside `self.legend_show_check.toggled.connect(self._on_chart_config_changed)`:

```python
        self.legend_show_check.toggled.connect(self._on_chart_config_changed)
        self.legend_position_combo.currentIndexChanged.connect(self._on_chart_config_changed)
        self.legend_font_size_spin.valueChanged.connect(self._on_chart_config_changed)
        self.legend_bg_color_button.colorChanged.connect(self._on_chart_config_changed)
        self.legend_show_frame_check.toggled.connect(self._on_chart_config_changed)
```

- [ ] **Step 3: Write the values in `_on_chart_config_changed` and `apply_to_chart`**

In `_on_chart_config_changed`, alongside `config["show_legend"] = ...`:

```python
        if hasattr(self, "legend_show_check"):
            config["show_legend"] = self.legend_show_check.isChecked()
        if hasattr(self, "legend_position_combo") and self.legend_position_combo.currentData():
            config["legend_position"] = self.legend_position_combo.currentData().value
        if hasattr(self, "legend_font_size_spin"):
            config["legend_font_size"] = self.legend_font_size_spin.value()
        if hasattr(self, "legend_bg_color_button"):
            config["legend_bg_color"] = self.legend_bg_color_button.get_color()
        if hasattr(self, "legend_show_frame_check"):
            config["legend_show_frame"] = self.legend_show_frame_check.isChecked()
```

In `apply_to_chart`, alongside `chart.config["show_legend"] = ...`:

```python
        chart.config["show_legend"] = self.legend_show_check.isChecked()
        if self.legend_position_combo.currentData():
            chart.config["legend_position"] = self.legend_position_combo.currentData().value
        chart.config["legend_font_size"] = self.legend_font_size_spin.value()
        chart.config["legend_bg_color"] = self.legend_bg_color_button.get_color()
        chart.config["legend_show_frame"] = self.legend_show_frame_check.isChecked()
```

- [ ] **Step 4: Load the values in `load_chart_object`**

Alongside `self.legend_show_check.setChecked(config.get("show_legend", True))`:

```python
            self.legend_show_check.setChecked(config.get("show_legend", True))
            legend_position_value = config.get("legend_position", "upper right")
            for i in range(self.legend_position_combo.count()):
                if (self.legend_position_combo.itemData(i)
                        and self.legend_position_combo.itemData(i).value == legend_position_value):
                    self.legend_position_combo.setCurrentIndex(i)
                    break
            self.legend_font_size_spin.setValue(config.get("legend_font_size", 10))
            self.legend_bg_color_button.set_color(config.get("legend_bg_color", "#ffffff"))
            self.legend_show_frame_check.setChecked(config.get("legend_show_frame", True))
```

- [ ] **Step 5: Apply legend styling in the renderer**

In `pandaplot/gui/components/tabs/chart/chart_editor.py`, replace:

```python
            if config.get("show_legend", True) and (self.chart.data_series or self.chart.fit_data):
                self.chart_canvas.axes.legend(
                    loc=config.get("legend_position", "upper right"))
```

with:

```python
            if config.get("show_legend", True) and (self.chart.data_series or self.chart.fit_data):
                self.chart_canvas.axes.legend(
                    loc=config.get("legend_position", "upper right"),
                    fontsize=config.get("legend_font_size", 10),
                    facecolor=config.get("legend_bg_color", "#ffffff"),
                    frameon=config.get("legend_show_frame", True))
```

- [ ] **Step 6: Manually verify in the running app**

Run: `python -m pandaplot`

1. Open a chart with at least two labeled series (so the legend is visible). In the Legend tab, change Position to a different corner (e.g. "Lower Left") and Apply. Confirm the legend box moves.
2. Change Font Size and Apply. Confirm the legend text size changes.
3. Change Background color and Apply. Confirm the legend box background color changes.
4. Uncheck "Show Frame" and Apply. Confirm the legend's border disappears. Re-check it; confirm the border returns.
5. Save and reopen the project; confirm all four settings persist.

- [ ] **Step 7: Commit**

```bash
git add pandaplot/gui/components/sidebar/chart/chart_properties_panel.py pandaplot/gui/components/tabs/chart/chart_editor.py
git commit -m "Wire Legend Position/Font Size/Background and add Show Frame toggle"
```

---

### Task 9: Full regression pass

**Files:** none (verification only)

- [ ] **Step 1: Run the full automated test suite**

Run: `pytest -v`
Expected: PASS — all tests including `tests/models/test_chart_line_style.py`, `tests/models/test_chart_style_axes_legend_config.py`, and `tests/gui/test_chart_editor_tick_helpers.py`.

- [ ] **Step 2: Run linting**

Run: `ruff check pandaplot`
Expected: no new errors introduced by this plan's changes.

- [ ] **Step 3: End-to-end manual pass in the running app**

Run: `python -m pandaplot`

Create one chart and, in a single session, exercise every control changed by this plan (per-axis grid, transparency, font size, scale, limits, ticks, legend) together, then save and reopen the project to confirm the entire combined configuration round-trips correctly with no fields reverting or conflicting with each other.

- [ ] **Step 4: Commit (only if Steps 1-3 required fixes)**

```bash
git add -A
git commit -m "Fix regressions found in full pass over plot sidebar changes"
```
