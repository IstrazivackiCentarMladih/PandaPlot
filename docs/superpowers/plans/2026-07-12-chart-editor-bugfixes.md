# Chart Editor Bug Fixes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix five chart-editor bugs: zoom resets on any style change, zoom isn't persisted across tab switches or reopening the project, marker size can't go below 1.0, the grid checkboxes are invisible (white-on-white), and the grid looks wrong on a log-scale axis with auto ticks. Also add mouse-wheel zoom.

**Architecture:** Persist the user's current pan/zoom into `chart.config` (`zoom_xlim`/`zoom_ylim`), restored on every redraw when auto-limits are in effect, captured via matplotlib's `xlim_changed`/`ylim_changed` axes callbacks (reconnected after every `axes.clear()`, since `clear()` drops existing callback registrations — verified directly). Add mouse-wheel zoom via matplotlib's existing `scroll_event`, which Qt's `FigureCanvasQT.wheelEvent` already forwards.

**Tech Stack:** PySide6, matplotlib (`FigureCanvasQTAgg`), pytest.

## Global Constraints

- Zoom persists to the chart file (per your request) — new `chart.config` keys `zoom_xlim`/`zoom_ylim` (each `Optional[List[float]]`, default `None`), read via `.get(key, default)` everywhere so old saved charts are unaffected.
- Manual axis limits (the `x_auto_limits`/`y_auto_limits` config from prior work) always take priority over a stored zoom — zoom restore only applies when the corresponding axis is in auto mode.
- Do not touch the separate/legacy `ChartConfiguration`/`ChartStyleManager` path — same boundary as prior work.
- Follow existing test convention: plain pytest functions, no fixtures/classes. GUI-only changes (checkbox styling, wheel event, tab-switch behavior) have no automated-test precedent in this repo (no pytest-qt) — verify by code review + manual checklist.
- Run tests with `pytest` from the repo root.

---

### Task 1: Persist and restore chart zoom across redraws

**Files:**
- Modify: `pandaplot/models/project/items/chart.py`
- Modify: `pandaplot/gui/components/tabs/chart/chart_editor.py`
- Test: `tests/gui/test_chart_editor_zoom.py`

**Interfaces:**
- Produces: `Chart.config["zoom_xlim"]`, `Chart.config["zoom_ylim"]` (default `None`).
- Produces: module-level `restore_zoom(axes, x_auto_limits, zoom_xlim, y_auto_limits, zoom_ylim)` in `chart_editor.py`, next to the existing `apply_axis_ticks` helper — pure, testable against a real matplotlib `Axes` (Agg backend, no Qt).

- [ ] **Step 1: Add the two new config keys**

In `pandaplot/models/project/items/chart.py`, in `_init_default_config()`, add to the `self.config = {...}` dict (anywhere, e.g. after `"y_tick_format_custom": ""`):

```python
            "zoom_xlim": None,
            "zoom_ylim": None,
```

- [ ] **Step 2: Write the failing test for `restore_zoom`**

Create `tests/gui/test_chart_editor_zoom.py`:

```python
"""
Unit tests for restore_zoom(), the pure helper that re-applies a user's
last pan/zoom after ChartEditorWidget.update_chart() clears the axes.
"""

import matplotlib
matplotlib.use("Agg")

from matplotlib.figure import Figure

from pandaplot.gui.components.tabs.chart.chart_editor import restore_zoom


def _make_axes():
    fig = Figure()
    return fig.add_subplot(111)


def test_restores_x_zoom_when_auto_limits_true():
    axes = _make_axes()
    restore_zoom(axes, True, [2.0, 8.0], True, None)
    assert axes.get_xlim() == (2.0, 8.0)


def test_restores_y_zoom_when_auto_limits_true():
    axes = _make_axes()
    restore_zoom(axes, True, None, True, [1.0, 9.0])
    assert axes.get_ylim() == (1.0, 9.0)


def test_does_not_restore_x_zoom_when_manual_limits_active():
    axes = _make_axes()
    default_xlim = axes.get_xlim()
    restore_zoom(axes, False, [2.0, 8.0], True, None)
    assert axes.get_xlim() == default_xlim


def test_does_nothing_when_no_zoom_stored():
    axes = _make_axes()
    default_xlim = axes.get_xlim()
    default_ylim = axes.get_ylim()
    restore_zoom(axes, True, None, True, None)
    assert axes.get_xlim() == default_xlim
    assert axes.get_ylim() == default_ylim
```

- [ ] **Step 3: Run the test to verify it fails**

Run: `pytest tests/gui/test_chart_editor_zoom.py -v`
Expected: FAIL — `ImportError: cannot import name 'restore_zoom'`.

- [ ] **Step 4: Implement `restore_zoom`**

In `pandaplot/gui/components/tabs/chart/chart_editor.py`, add after the existing `apply_axis_ticks` function:

```python
def restore_zoom(axes, x_auto_limits, zoom_xlim, y_auto_limits, zoom_ylim):
    """Re-apply a previously stored pan/zoom, but only on axes still in auto-limits mode
    (explicit manual axis limits, applied earlier in update_chart, always take priority).
    """
    if x_auto_limits and zoom_xlim:
        axes.set_xlim(*zoom_xlim)
    if y_auto_limits and zoom_ylim:
        axes.set_ylim(*zoom_ylim)
```

- [ ] **Step 5: Run the test to verify it passes**

Run: `pytest tests/gui/test_chart_editor_zoom.py -v`
Expected: PASS (4 tests).

- [ ] **Step 6: Wire `restore_zoom` and view-change callbacks into `update_chart()`**

In `update_chart()`, replace:

```python
            self.chart_canvas.axes.grid(
                config.get("show_grid_x", True), axis="x", alpha=config.get("grid_alpha", 0.3))
            self.chart_canvas.axes.grid(
                config.get("show_grid_y", True), axis="y", alpha=config.get("grid_alpha", 0.3))
```

with (this also folds in Task 3's log-scale grid fix — see Task 3 below for why `which=` is added here):

```python
            self.chart_canvas.axes.grid(
                config.get("show_grid_x", True), axis="x",
                which="both" if config.get("x_scale", "linear") == "log" else "major",
                alpha=config.get("grid_alpha", 0.3))
            self.chart_canvas.axes.grid(
                config.get("show_grid_y", True), axis="y",
                which="both" if config.get("y_scale", "linear") == "log" else "major",
                alpha=config.get("grid_alpha", 0.3))

            # Restore the user's last pan/zoom (auto-limits axes only; manual limits above win)
            restore_zoom(
                self.chart_canvas.axes,
                config.get("x_auto_limits", True), config.get("zoom_xlim"),
                config.get("y_auto_limits", True), config.get("zoom_ylim"))

            # Reconnect view-change callbacks (axes.clear() at the top of this method
            # drops any previous connections) so future interactive pan/zoom gets captured
            self.chart_canvas.axes.callbacks.connect("xlim_changed", self._on_axes_view_changed)
            self.chart_canvas.axes.callbacks.connect("ylim_changed", self._on_axes_view_changed)
```

- [ ] **Step 7: Add the view-change callback handler**

Add a new method to `ChartEditorWidget`, near `_on_size_changed`:

```python
    def _on_axes_view_changed(self, ax):
        """Persist the user's current pan/zoom so it survives redraws, tab switches, and reloads."""
        self.chart.config["zoom_xlim"] = list(ax.get_xlim())
        self.chart.config["zoom_ylim"] = list(ax.get_ylim())
        self.chart.update_modified_time()
```

- [ ] **Step 8: Clear the stored zoom when the user explicitly resets it**

Replace:

```python
    def _on_reset_zoom(self):
        """Handle reset zoom action."""
        if hasattr(self, "chart_canvas"):
            self.chart_canvas.reset_zoom()
```

with:

```python
    def _on_reset_zoom(self):
        """Handle reset zoom action."""
        if hasattr(self, "chart_canvas"):
            self.chart_canvas.reset_zoom()
            self.chart.config["zoom_xlim"] = None
            self.chart.config["zoom_ylim"] = None
            self.chart.update_modified_time()
```

- [ ] **Step 9: Run the full suite to check for regressions**

Run: `pytest`
Expected: PASS (371 passed — 367 pre-existing + 4 new).

- [ ] **Step 10: Manually verify in the running app**

Run: `python -m pandaplot`

1. Open a chart, zoom in via the navigation toolbar's zoom tool. Change any Style/Axes/Legend setting and Apply. Confirm the chart stays zoomed instead of resetting to full-data view.
2. Switch to another tab and back. Confirm the zoom is still there.
3. Save the project, close and reopen it. Confirm the chart reopens at the same zoomed view.
4. Click "Reset Zoom". Confirm it returns to the full-data view, and stays there after another Style/Axes/Legend change (i.e. the cleared zoom doesn't come back).
5. With an axis's "Auto" limit unchecked (manual min/max set), zoom in, then Apply a style change — confirm the manual limits still win (not the zoom).

- [ ] **Step 11: Commit**

```bash
git add pandaplot/models/project/items/chart.py pandaplot/gui/components/tabs/chart/chart_editor.py tests/gui/test_chart_editor_zoom.py
git commit -m "Persist and restore chart zoom across redraws, tab switches, and reloads"
```

---

### Task 2: Mouse-wheel zoom on the plot

**Files:**
- Modify: `pandaplot/gui/components/tabs/chart/chart_canvas.py`

**Interfaces:** none new; connects to matplotlib's existing `scroll_event`.

No automated test — real Qt/matplotlib event handling, no Qt test infra in this repo. Verify by code review + manual check (Step 3).

Matplotlib's `FigureCanvasQT.wheelEvent` (base class `ChartCanvas` inherits from) already translates Qt wheel events into matplotlib's own `scroll_event` — we just need to connect a handler for it, which is the standard scroll-to-zoom recipe.

- [ ] **Step 1: Add the scroll-zoom handler and connect it**

In `pandaplot/gui/components/tabs/chart/chart_canvas.py`, add a method to `ChartCanvas`:

```python
    def _on_scroll(self, event):
        """Zoom in/out on mouse wheel, centered on the cursor position."""
        if event.inaxes is None:
            return
        axes = event.inaxes
        scale_factor = 0.9 if event.step > 0 else 1.1
        xdata, ydata = event.xdata, event.ydata
        x_min, x_max = axes.get_xlim()
        y_min, y_max = axes.get_ylim()
        axes.set_xlim(xdata - (xdata - x_min) * scale_factor, xdata + (x_max - xdata) * scale_factor)
        axes.set_ylim(ydata - (ydata - y_min) * scale_factor, ydata + (y_max - ydata) * scale_factor)
        self.draw()
```

In `__init__`, after `self.setup_navigation()`, add:

```python
        self.mpl_connect("scroll_event", self._on_scroll)
```

- [ ] **Step 2: Run the full suite to check for regressions**

Run: `pytest`
Expected: PASS (371 passed, no new tests in this task).

- [ ] **Step 3: Manually verify in the running app**

Run: `python -m pandaplot`

1. Open a chart. Hover over the plot and scroll the mouse wheel up; confirm it zooms in, centered near the cursor.
2. Scroll down; confirm it zooms back out.
3. Confirm the resulting zoom also persists across a style change and tab switch (Task 1's fix applies here too, since wheel-zoom goes through the same `set_xlim`/`set_ylim` calls that trigger the view-change callbacks).

- [ ] **Step 4: Commit**

```bash
git add pandaplot/gui/components/tabs/chart/chart_canvas.py
git commit -m "Add mouse-wheel zoom on the chart preview"
```

---

### Task 3: Fix log-scale grid and marker size minimum

**Files:**
- Modify: `pandaplot/gui/components/sidebar/chart/chart_properties_panel.py`

**Interfaces:** none new.

The log-scale grid fix (`which="both"` on the `axes.grid()` calls) was already applied in Task 1, Step 6, since it's in the exact same two lines Task 1 needed to touch anyway — no separate edit needed here. This task only changes the marker size spinbox range.

No automated test — a `QDoubleSpinBox.setRange()` call, no behavior to unit test beyond what Qt itself guarantees. Verify by code review + manual check (Step 2).

- [ ] **Step 1: Lower the marker size minimum to 0**

In `_create_style_tab`, replace:

```python
        self.marker_size_spin.setRange(1.0, 20.0)
```

with:

```python
        self.marker_size_spin.setRange(0.0, 20.0)
```

- [ ] **Step 2: Manually verify in the running app**

Run: `python -m pandaplot`

1. Open a chart with a line or scatter series. In the Style tab, set Marker Size down to 0. Confirm it's accepted (was previously floored at 1) and the marker disappears from the rendered chart (matplotlib treats `markersize=0`/`s=0` as invisible, same as marker style "None").
2. Set an X or Y axis to Log scale with a numeric dataset that has strictly positive values, with Show Grid on and Tick Mode "Auto". Confirm gridlines now appear at both major (decade) and minor (2,3,4...9) tick positions instead of only at decades.

- [ ] **Step 3: Commit**

```bash
git add pandaplot/gui/components/sidebar/chart/chart_properties_panel.py
git commit -m "Allow marker size down to 0 and fix log-scale grid density"
```

---

### Task 4: Make the grid checkboxes visible

**Files:**
- Modify: `pandaplot/gui/components/sidebar/chart/chart_properties_panel.py`

**Interfaces:** none new.

No automated test — pure Qt stylesheet change. Verify by code review + manual check (Step 3), ideally in both light and dark theme.

Root cause: the theme manager never sets checkbox indicator colors (only text/background palette roles), and no `QCheckBox`/`QCheckBox::indicator` stylesheet rule exists anywhere in the panel, so the native OS-drawn checkbox indicator (near-white box and tick) renders low-contrast against the panel's own near-white background in the light theme.

- [ ] **Step 1: Add an `accent` color lookup**

In `_apply_theme`, replace:

```python
        # Get theme colors with fallbacks
        card_bg = palette.get("card_bg", "#ffffff")
        card_border = palette.get("card_border", "#dee2e6")
        base_fg = palette.get("base_fg", "#333333")
        card_hover = palette.get("card_hover", "#e5f3ff")
```

with:

```python
        # Get theme colors with fallbacks
        card_bg = palette.get("card_bg", "#ffffff")
        card_border = palette.get("card_border", "#dee2e6")
        base_fg = palette.get("base_fg", "#333333")
        card_hover = palette.get("card_hover", "#e5f3ff")
        accent = palette.get("accent", "#4A90E2")
```

- [ ] **Step 2: Add explicit checkbox styling to the panel-level stylesheet**

Replace:

```python
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
                background-color: {card_bg};
            }}
        """)
```

with:

```python
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
                background-color: {card_bg};
            }}
            QCheckBox {{
                color: {base_fg};
                spacing: 6px;
            }}
            QCheckBox::indicator {{
                width: 14px;
                height: 14px;
                border: 1px solid {card_border};
                border-radius: 3px;
                background-color: {card_bg};
            }}
            QCheckBox::indicator:checked {{
                background-color: {accent};
                border: 1px solid {accent};
            }}
        """)
```

- [ ] **Step 3: Manually verify in the running app, in both themes**

Run: `python -m pandaplot`

1. Open a chart's properties sidebar (Axes tab, Legend tab). Confirm the "Show Grid"/"Show Legend"/"Show Frame" checkboxes now show a visible bordered box, and a colored (accent) fill with a visible checkmark when checked.
2. Switch the app's theme (light/dark, via Settings) and repeat — confirm checkboxes stay visible/legible in both.

- [ ] **Step 4: Commit**

```bash
git add pandaplot/gui/components/sidebar/chart/chart_properties_panel.py
git commit -m "Fix invisible grid/legend checkboxes with explicit theme-aware styling"
```
