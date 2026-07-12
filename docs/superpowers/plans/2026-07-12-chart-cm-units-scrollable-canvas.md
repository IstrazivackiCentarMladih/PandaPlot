# Chart cm Units & Scrollable Canvas Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Switch the chart preview's width/height controls from inches to centimeters, and make the preview area actually scroll when the configured chart size exceeds the visible viewport.

**Architecture:** Add a pure cm↔inches conversion helper next to `ChartCanvas` (matplotlib's `Figure` is hard-wired to inches internally, so the conversion boundary sits right at the `ChartCanvas`/`set_size()` call). Fix scrolling by disabling `QScrollArea.setWidgetResizable` (which currently force-fits the canvas to the viewport) and switching the canvas to a fixed size policy driven by its true pixel dimensions (`width_in × dpi`, `height_in × dpi`).

**Tech Stack:** PySide6, matplotlib (`FigureCanvasQTAgg`), pytest.

## Global Constraints

- Sizing stays session-only (not persisted to `chart.style`) — matches current behavior, no scope change here.
- Do not touch the separate/legacy `ChartConfiguration`/`ChartStyleManager` figure_size path (`pandaplot/models/chart/chart_configuration.py`, `pandaplot/models/chart/chart_style_manager.py`) — out of scope, same boundary as prior work on this sidebar.
- No project-file migration concerns (nothing new is persisted).
- Follow existing test convention: plain pytest functions, no fixtures/classes, mirroring `tests/gui/test_chart_editor_tick_helpers.py`'s style. GUI wiring changes with no automated-test precedent (no pytest-qt in this repo) are verified by code review + a documented manual-verification checklist, not claimed interactive testing.
- Run tests with `pytest` from the repo root.

---

### Task 1: Add cm↔inches conversion helpers

**Files:**
- Modify: `pandaplot/gui/components/tabs/chart/chart_canvas.py`
- Test: `tests/gui/test_chart_canvas_units.py`

**Interfaces:**
- Produces: `cm_to_inches(cm: float) -> float` and `inches_to_cm(inches: float) -> float`, module-level functions in `chart_canvas.py`, importable as `from pandaplot.gui.components.tabs.chart.chart_canvas import cm_to_inches, inches_to_cm`. Task 2 uses `cm_to_inches` to convert the width/height spinbox values before they reach `ChartCanvas`/`set_size()`.

- [ ] **Step 1: Write the failing tests**

Create `tests/gui/test_chart_canvas_units.py`:

```python
"""
Unit tests for the cm<->inches conversion helpers used to let the chart
preview's width/height controls work in centimeters, while matplotlib's
Figure stays in inches internally (a hard API constraint).
"""

import pytest

from pandaplot.gui.components.tabs.chart.chart_canvas import cm_to_inches, inches_to_cm


def test_cm_to_inches_known_value():
    assert cm_to_inches(2.54) == pytest.approx(1.0)


def test_inches_to_cm_known_value():
    assert inches_to_cm(1.0) == pytest.approx(2.54)


def test_cm_to_inches_round_trips_with_inches_to_cm():
    assert inches_to_cm(cm_to_inches(20.0)) == pytest.approx(20.0)


def test_default_width_cm_converts_to_expected_inches():
    assert cm_to_inches(20.0) == pytest.approx(7.874, abs=1e-3)


def test_default_height_cm_converts_to_expected_inches():
    assert cm_to_inches(15.0) == pytest.approx(5.906, abs=1e-3)
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `pytest tests/gui/test_chart_canvas_units.py -v`
Expected: FAIL — `ImportError: cannot import name 'cm_to_inches'`.

- [ ] **Step 3: Implement the helpers**

In `pandaplot/gui/components/tabs/chart/chart_canvas.py`, add after the existing imports, before `class ChartCanvas`:

```python
CM_PER_INCH = 2.54


def cm_to_inches(cm):
    """Convert centimeters to inches (matplotlib's Figure sizing is always in inches)."""
    return cm / CM_PER_INCH


def inches_to_cm(inches):
    """Convert inches to centimeters."""
    return inches * CM_PER_INCH
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `pytest tests/gui/test_chart_canvas_units.py -v`
Expected: PASS (5 tests).

- [ ] **Step 5: Run the full suite to check for regressions**

Run: `pytest`
Expected: PASS (367 passed — 362 pre-existing + 5 new tests).

- [ ] **Step 6: Commit**

```bash
git add pandaplot/gui/components/tabs/chart/chart_canvas.py tests/gui/test_chart_canvas_units.py
git commit -m "Add cm/inches conversion helpers for chart size controls"
```

---

### Task 2: Switch chart size controls to centimeters

**Files:**
- Modify: `pandaplot/gui/components/tabs/chart/chart_editor.py`

**Interfaces:**
- Consumes: `cm_to_inches` from Task 1.
- Produces: no new interfaces; `width_spin`/`height_spin` now hold cm values, `chart_canvas` still receives inches internally.

No automated test for this task — pure Qt widget config + a unit-conversion call site, exercised by Task 1's tests already. Verify by code review; the manual steps below require a GUI-capable environment.

- [ ] **Step 1: Import the conversion helper**

In `pandaplot/gui/components/tabs/chart/chart_editor.py`, change:

```python
from pandaplot.gui.components.tabs.chart.chart_canvas import ChartCanvas
```

to:

```python
from pandaplot.gui.components.tabs.chart.chart_canvas import ChartCanvas, cm_to_inches
```

- [ ] **Step 2: Change the width/height spinboxes to centimeters**

Replace:

```python
        # Width control
        self.width_spin = QSpinBox()
        self.width_spin.setRange(4, 20)
        self.width_spin.setValue(8)
        self.width_spin.setSuffix(" in")
        self.width_spin.setToolTip("Chart width in inches")
        self.width_spin.valueChanged.connect(self._on_size_changed)
        self.preview_toolbar.addWidget(self.width_spin)

        self.multiply_label = QLabel("×")
        self.preview_toolbar.addWidget(self.multiply_label)

        # Height control
        self.height_spin = QSpinBox()
        self.height_spin.setRange(3, 15)
        self.height_spin.setValue(6)
        self.height_spin.setSuffix(" in")
        self.height_spin.setToolTip("Chart height in inches")
        self.height_spin.valueChanged.connect(self._on_size_changed)
        self.preview_toolbar.addWidget(self.height_spin)
```

with:

```python
        # Width control
        self.width_spin = QSpinBox()
        self.width_spin.setRange(10, 50)
        self.width_spin.setValue(20)
        self.width_spin.setSuffix(" cm")
        self.width_spin.setToolTip("Chart width in centimeters")
        self.width_spin.valueChanged.connect(self._on_size_changed)
        self.preview_toolbar.addWidget(self.width_spin)

        self.multiply_label = QLabel("×")
        self.preview_toolbar.addWidget(self.multiply_label)

        # Height control
        self.height_spin = QSpinBox()
        self.height_spin.setRange(8, 40)
        self.height_spin.setValue(15)
        self.height_spin.setSuffix(" cm")
        self.height_spin.setToolTip("Chart height in centimeters")
        self.height_spin.valueChanged.connect(self._on_size_changed)
        self.preview_toolbar.addWidget(self.height_spin)
```

- [ ] **Step 3: Convert the initial `ChartCanvas` construction to match the new cm defaults**

Replace:

```python
        self.chart_canvas = ChartCanvas(width=8, height=6, dpi=dpi)
```

with:

```python
        self.chart_canvas = ChartCanvas(width=cm_to_inches(20), height=cm_to_inches(15), dpi=dpi)
```

- [ ] **Step 4: Convert cm to inches in `_on_size_changed`**

Replace:

```python
    def _on_size_changed(self):
        """Handle chart size changes."""
        if hasattr(self, "chart_canvas"):
            width = self.width_spin.value()
            height = self.height_spin.value()
            self.chart_canvas.set_size(width, height)
            self.update_status("Chart size updated")
```

with:

```python
    def _on_size_changed(self):
        """Handle chart size changes."""
        if hasattr(self, "chart_canvas"):
            width = cm_to_inches(self.width_spin.value())
            height = cm_to_inches(self.height_spin.value())
            self.chart_canvas.set_size(width, height)
            self.update_status("Chart size updated")
```

- [ ] **Step 5: Run the full suite to check for regressions**

Run: `pytest`
Expected: PASS (367 passed, no new tests added in this task).

- [ ] **Step 6: Manually verify in the running app**

Run: `python -m pandaplot`

1. Open a chart. Confirm the toolbar's size spinboxes read "20 cm" and "15 cm" (not "8 in"/"6 in").
2. Change width/height and confirm the chart visibly resizes and the status bar shows "Chart size updated".
3. Confirm the spinbox range allows 10-50 cm (width) and 8-40 cm (height).

- [ ] **Step 7: Commit**

```bash
git add pandaplot/gui/components/tabs/chart/chart_editor.py
git commit -m "Switch chart size controls from inches to centimeters"
```

---

### Task 3: Make the chart preview scrollable when it exceeds the viewport

**Files:**
- Modify: `pandaplot/gui/components/tabs/chart/chart_canvas.py`
- Modify: `pandaplot/gui/components/tabs/chart/chart_editor.py`

**Interfaces:** none new; this task only changes widget sizing behavior.

No automated test — this is real Qt/matplotlib widget geometry behavior with no headless test precedent in this repo. Verify by code review plus the manual checklist in Step 4 (requires a GUI-capable environment).

Root cause: `QScrollArea.setWidgetResizable(True)` forces its child widget to always match the viewport size, so the canvas can never exceed the visible area and trigger scrollbars — regardless of the canvas's own configured size. `matplotlib`'s `FigureCanvasQTAgg.sizeHint()` returns the figure's true pixel size (`width_in × dpi`, `height_in × dpi`), but that's only honored by a widget with a `Fixed` (or similar non-stretching) size policy, and only after something tells Qt to re-query it (Qt doesn't watch `Figure.set_size_inches()` calls).

- [ ] **Step 1: Make `ChartCanvas.set_size()` resize itself to the new pixel dimensions**

In `pandaplot/gui/components/tabs/chart/chart_canvas.py`, replace:

```python
    def set_size(self, width, height):
        """Change the figure size."""
        self.fig.set_size_inches(width, height)
        self.fig.tight_layout()
        self.draw()
```

with:

```python
    def set_size(self, width, height):
        """Change the figure size."""
        self.fig.set_size_inches(width, height)
        self.fig.tight_layout()
        self.resize(*self.get_width_height())
        self.draw()
```

- [ ] **Step 2: Stop the scroll area from force-fitting the canvas, and give the canvas a fixed size policy**

In `pandaplot/gui/components/tabs/chart/chart_editor.py`, replace:

```python
        self.chart_canvas = ChartCanvas(width=cm_to_inches(20), height=cm_to_inches(15), dpi=dpi)
        self.chart_canvas.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
```

with:

```python
        self.chart_canvas = ChartCanvas(width=cm_to_inches(20), height=cm_to_inches(15), dpi=dpi)
        self.chart_canvas.setSizePolicy(
            QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
```

Then replace:

```python
        # Wrap chart canvas in scroll area for large charts
        canvas_scroll = QScrollArea()
        canvas_scroll.setWidgetResizable(True)
        canvas_scroll.setWidget(self.chart_canvas)
        canvas_scroll.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding
        )
        canvas_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        canvas_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
```

with:

```python
        # Wrap chart canvas in scroll area for large charts
        canvas_scroll = QScrollArea()
        canvas_scroll.setWidgetResizable(False)
        canvas_scroll.setWidget(self.chart_canvas)
        canvas_scroll.setAlignment(Qt.AlignmentFlag.AlignCenter)
        canvas_scroll.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding
        )
        canvas_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        canvas_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
```

- [ ] **Step 3: Keep the canvas's pixel size in sync when the global DPI setting changes**

In `_on_config_updated`, replace:

```python
            dpi = getattr(getattr(cfg, "chart_display", None), "dpi", None)
            if dpi and self.chart_canvas and self.chart_canvas.fig.dpi != dpi:
                self.chart_canvas.fig.set_dpi(dpi)
                # Matplotlib may need a tight_layout or redraw
                try:
                    self.chart_canvas.fig.tight_layout()
                except Exception:
                    pass
                self.chart_canvas.draw()
```

with:

```python
            dpi = getattr(getattr(cfg, "chart_display", None), "dpi", None)
            if dpi and self.chart_canvas and self.chart_canvas.fig.dpi != dpi:
                self.chart_canvas.fig.set_dpi(dpi)
                # Matplotlib may need a tight_layout or redraw
                try:
                    self.chart_canvas.fig.tight_layout()
                except Exception:
                    pass
                self.chart_canvas.resize(*self.chart_canvas.get_width_height())
                self.chart_canvas.draw()
```

(Without this, changing the global DPI preference would change the figure's pixel size but leave the widget's on-screen size stale, since the canvas is no longer force-resized by the scroll area.)

- [ ] **Step 4: Run the full suite, then manually verify in the running app**

Run: `pytest`
Expected: PASS (367 passed, no regressions).

Run: `python -m pandaplot`

1. Open a chart. Set width/height to a large value (e.g. 50 × 40 cm) via the toolbar spinboxes. Confirm the chart renders at its full configured size and horizontal/vertical scrollbars appear on the surrounding scroll area rather than the chart being squeezed to fit the visible panel.
2. Scroll within the preview area and confirm you can pan to see all parts of the oversized chart.
3. Set width/height back down to something smaller than the visible panel (e.g. 10 × 8 cm). Confirm the chart renders at that smaller size, centered in the scroll area, with no scrollbars.
4. Resize the main application window. Confirm the chart's own size doesn't change (it's driven only by the spinboxes now) — only the amount of visible/scrollable area changes.
5. If accessible, open Settings and change the chart DPI preference; confirm the open chart's on-screen size updates to match (no stale/clipped rendering).

- [ ] **Step 5: Commit**

```bash
git add pandaplot/gui/components/tabs/chart/chart_canvas.py pandaplot/gui/components/tabs/chart/chart_editor.py
git commit -m "Make the chart preview scrollable when it exceeds the viewport"
```
