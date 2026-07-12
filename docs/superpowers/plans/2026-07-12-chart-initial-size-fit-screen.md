# Chart Initial Size: Fit the Preview Panel Unless Saved Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A chart with no previously-saved size opens sized to fit the visible preview panel; a chart that's been resized before (or already fitted once) reopens at that saved size; width/height persist to `chart.config` via the existing (currently-unused) auto-save timer.

**Architecture:** Extract the pixel→cm fit computation into a small pure function (`fit_size_cm`) next to the existing `cm_to_inches`/`inches_to_cm` helpers in `chart_canvas.py`, so the size math is unit-testable without Qt. `chart_editor.py` gets a `_resize_canvas` helper (pure canvas resize, no persistence) used by both the "load a saved size silently" path and the "user dragged a spinbox" path, and the existing `_on_size_changed` becomes the only path that writes to `chart.config` and marks the chart modified. `load_chart_config` branches on whether `chart.config` has a saved size: if yes, apply it silently; if no, defer (via the same 100ms-settle pattern already used for `_apply_theme`) to a new `_fit_size_to_preview_panel` method that measures the scroll area's viewport and applies the fitted size through the normal (persisting) path.

**Tech Stack:** PySide6, matplotlib (`FigureCanvasQTAgg`), pytest.

## Global Constraints

- No project-file migration: `width_cm`/`height_cm` are read via `chart.config.get(key, None)`; their absence means "unset," and `Chart._init_default_config()` is not changed to include them (this is also what makes `reset_chart()` naturally clear a saved size back to "unset").
- Spinbox minimums become 2cm (width) / 2cm (height); maximums stay 50cm / 40cm.
- Follow existing test convention: plain pytest functions, no fixtures/classes. GUI wiring changes with no automated-test precedent (no pytest-qt in this repo) are verified by code review + a documented manual-verification checklist, matching `tests/gui/test_chart_editor_tick_helpers.py`'s pattern of testing extracted pure functions against real matplotlib objects rather than through Qt.
- Run tests with `pytest` from the repo root.
- Fit-to-panel only ever runs once per chart (the first time it's opened with no saved size) — a saved size is always reused as-is afterward, never re-fit on window/panel resize.

---

### Task 1: Add `fit_size_cm()` pure helper for the fit-to-panel computation

**Files:**
- Modify: `pandaplot/gui/components/tabs/chart/chart_canvas.py`
- Test: `tests/gui/test_chart_canvas_units.py`

**Interfaces:**
- Produces: `fit_size_cm(viewport_width_px, viewport_height_px, dpi, min_width_cm=2, max_width_cm=50, min_height_cm=2, max_height_cm=40) -> tuple[int, int]`, module-level function in `chart_canvas.py`, importable as `from pandaplot.gui.components.tabs.chart.chart_canvas import fit_size_cm`. Task 3 uses this from `ChartEditorWidget._fit_size_to_preview_panel` to convert the preview scroll area's pixel viewport size into a clamped, rounded `(width_cm, height_cm)` pair.

- [ ] **Step 1: Write the failing tests**

Append to `tests/gui/test_chart_canvas_units.py`:

```python
from pandaplot.gui.components.tabs.chart.chart_canvas import fit_size_cm


def test_fit_size_cm_converts_pixels_to_cm_via_dpi():
    # 100 dpi, 393.7 px wide/tall ~= 3.937 in ~= 10.0 cm
    width_cm, height_cm = fit_size_cm(394, 394, dpi=100)
    assert width_cm == pytest.approx(10, abs=1)
    assert height_cm == pytest.approx(10, abs=1)


def test_fit_size_cm_clamps_to_minimums():
    width_cm, height_cm = fit_size_cm(10, 10, dpi=100)
    assert width_cm == 2
    assert height_cm == 2


def test_fit_size_cm_clamps_to_maximums():
    width_cm, height_cm = fit_size_cm(100000, 100000, dpi=100)
    assert width_cm == 50
    assert height_cm == 40


def test_fit_size_cm_returns_ints():
    width_cm, height_cm = fit_size_cm(500, 400, dpi=100)
    assert isinstance(width_cm, int)
    assert isinstance(height_cm, int)


def test_fit_size_cm_respects_custom_bounds():
    width_cm, height_cm = fit_size_cm(10, 10, dpi=100, min_width_cm=5, min_height_cm=6)
    assert width_cm == 5
    assert height_cm == 6
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `pytest tests/gui/test_chart_canvas_units.py -v`
Expected: FAIL — `ImportError: cannot import name 'fit_size_cm'`.

- [ ] **Step 3: Implement `fit_size_cm`**

In `pandaplot/gui/components/tabs/chart/chart_canvas.py`, add after `inches_to_cm`:

```python
def fit_size_cm(viewport_width_px, viewport_height_px, dpi,
                 min_width_cm=2, max_width_cm=50,
                 min_height_cm=2, max_height_cm=40):
    """Convert a pixel viewport size to a clamped, whole-cm chart size.

    Used to size a chart's initial preview to fill the visible preview
    panel when no size has been saved for it yet.
    """
    width_cm = inches_to_cm(viewport_width_px / dpi)
    height_cm = inches_to_cm(viewport_height_px / dpi)
    width_cm = max(min_width_cm, min(max_width_cm, round(width_cm)))
    height_cm = max(min_height_cm, min(max_height_cm, round(height_cm)))
    return width_cm, height_cm
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `pytest tests/gui/test_chart_canvas_units.py -v`
Expected: PASS (10 tests — 5 pre-existing + 5 new).

- [ ] **Step 5: Run the full suite to check for regressions**

Run: `pytest`
Expected: PASS, no regressions.

- [ ] **Step 6: Commit**

```bash
git add pandaplot/gui/components/tabs/chart/chart_canvas.py tests/gui/test_chart_canvas_units.py
git commit -m "Add fit_size_cm helper for chart fit-to-panel sizing"
```

---

### Task 2: Loosen the chart size spinbox minimums to 2cm

**Files:**
- Modify: `pandaplot/gui/components/tabs/chart/chart_editor.py`

**Interfaces:** none new; pure widget config change.

No automated test — this is a `QSpinBox.setRange()` config value, exercised only through the running app (no pytest-qt in this repo, matching the prior cm-units plan's convention for pure Qt widget config).

- [ ] **Step 1: Change the width/height spinbox ranges**

In `create_chart_preview_section`, replace:

```python
        self.width_spin.setRange(10, 50)
```

with:

```python
        self.width_spin.setRange(2, 50)
```

Replace:

```python
        self.height_spin.setRange(8, 40)
```

with:

```python
        self.height_spin.setRange(2, 40)
```

- [ ] **Step 2: Run the full suite to check for regressions**

Run: `pytest`
Expected: PASS, no regressions (no tests reference these ranges).

- [ ] **Step 3: Manually verify in the running app**

Run: `python -m pandaplot`

1. Open a chart. Drag the width spinbox down — confirm it now stops at 2 cm (not 10 cm).
2. Drag the height spinbox down — confirm it now stops at 2 cm (not 8 cm).

- [ ] **Step 4: Commit**

```bash
git add pandaplot/gui/components/tabs/chart/chart_editor.py
git commit -m "Allow chart size spinboxes down to 2cm"
```

---

### Task 3: Persist chart size and fit to the preview panel when nothing's saved

**Files:**
- Modify: `pandaplot/gui/components/tabs/chart/chart_editor.py`

**Interfaces:**
- Consumes: `fit_size_cm` from Task 1 (`from pandaplot.gui.components.tabs.chart.chart_canvas import ChartCanvas, cm_to_inches, fit_size_cm`).
- Produces: `ChartEditorWidget._resize_canvas(width_cm, height_cm)` (pure canvas resize, no persistence, no modified-flag) and `ChartEditorWidget._fit_size_to_preview_panel()` (computes and applies a fit-to-panel size the first time a chart has no saved size). `self.canvas_scroll` becomes an instance attribute (previously a local variable in `create_chart_preview_section`).

No automated test — this is real Qt widget wiring and persistence-on-user-interaction behavior with no headless test precedent in this repo (matching the prior cm-units/scrollable-canvas plan's convention). Verified by code review plus the manual checklist in Step 6.

- [ ] **Step 1: Import `fit_size_cm`**

Replace:

```python
from pandaplot.gui.components.tabs.chart.chart_canvas import ChartCanvas, cm_to_inches
```

with:

```python
from pandaplot.gui.components.tabs.chart.chart_canvas import ChartCanvas, cm_to_inches, fit_size_cm
```

- [ ] **Step 2: Make `canvas_scroll` an instance attribute**

In `create_chart_preview_section`, replace:

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

        preview_layout.addWidget(canvas_scroll)
```

with:

```python
        # Wrap chart canvas in scroll area for large charts
        self.canvas_scroll = QScrollArea()
        self.canvas_scroll.setWidgetResizable(False)
        self.canvas_scroll.setWidget(self.chart_canvas)
        self.canvas_scroll.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.canvas_scroll.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding
        )
        self.canvas_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.canvas_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        preview_layout.addWidget(self.canvas_scroll)
```

- [ ] **Step 3: Split canvas resizing from persistence in `_on_size_changed`, add `_resize_canvas`**

Replace:

```python
    def _on_size_changed(self):
        """Handle chart size changes."""
        if hasattr(self, "chart_canvas"):
            try:
                width = cm_to_inches(self.width_spin.value())
                height = cm_to_inches(self.height_spin.value())
                self.chart_canvas.set_size(width, height)
                self.update_status("Chart size updated")
            except Exception as e:
                self.update_status(f"Resize error: {str(e)}")

            # Reset status after 2 seconds
            QTimer.singleShot(2000, lambda: self.update_status("Ready"))
```

with:

```python
    def _resize_canvas(self, width_cm, height_cm):
        """Resize the canvas to the given cm size, without touching
        chart.config or the modified flag. Used both to silently apply a
        previously-saved size on load, and (via _on_size_changed) to apply
        an interactive resize."""
        self.chart_canvas.set_size(cm_to_inches(width_cm), cm_to_inches(height_cm))

    def _on_size_changed(self):
        """Handle interactive chart size changes: resize, persist, mark modified."""
        if hasattr(self, "chart_canvas"):
            try:
                width_cm = self.width_spin.value()
                height_cm = self.height_spin.value()
                self._resize_canvas(width_cm, height_cm)
                self.chart.config["width_cm"] = width_cm
                self.chart.config["height_cm"] = height_cm
                self.is_modified = True
                self.auto_save_timer.start(2000)
                self.update_status("Chart size updated")
            except Exception as e:
                self.update_status(f"Resize error: {str(e)}")

            # Reset status after 2 seconds
            QTimer.singleShot(2000, lambda: self.update_status("Ready"))
```

- [ ] **Step 4: Load a saved size silently, or defer to fit-to-panel**

Replace:

```python
    def load_chart_config(self):
        """Load chart configuration into UI controls."""
        # No configuration UI to load since it's now in the side panel
        pass
```

with:

```python
    def load_chart_config(self):
        """Load chart configuration into UI controls."""
        width_cm = self.chart.config.get("width_cm")
        height_cm = self.chart.config.get("height_cm")
        if width_cm is not None and height_cm is not None:
            self.width_spin.blockSignals(True)
            self.height_spin.blockSignals(True)
            self.width_spin.setValue(width_cm)
            self.height_spin.setValue(height_cm)
            self.width_spin.blockSignals(False)
            self.height_spin.blockSignals(False)
            self._resize_canvas(width_cm, height_cm)
        else:
            QTimer.singleShot(100, self._fit_size_to_preview_panel)

    def _fit_size_to_preview_panel(self):
        """Compute an initial chart size that fits the visible preview panel,
        for a chart that has never had a size saved. Applies via the normal
        size-changed path so the computed size is persisted and the chart
        won't need refitting next time it's opened."""
        if not isValid(self.chart_canvas):
            return
        viewport = self.canvas_scroll.viewport()
        dpi = self.chart_canvas.fig.dpi
        width_cm, height_cm = fit_size_cm(viewport.width(), viewport.height(), dpi)
        self.width_spin.setValue(width_cm)
        self.height_spin.setValue(height_cm)
```

- [ ] **Step 5: Run the full suite to check for regressions**

Run: `pytest`
Expected: PASS, no regressions.

- [ ] **Step 6: Manually verify in the running app**

Run: `python -m pandaplot`

1. Create a brand-new chart (no saved size). Open it. Confirm it opens sized to fill the preview panel with no scrollbars, and the width/height spinboxes reflect the fitted cm values (not a hardcoded 20/15).
2. Close the chart tab and reopen it. Confirm it now opens at the *same* size as step 1 (the previously-fitted size), not re-fit to the panel — i.e., the size stuck.
3. Drag the width/height spinboxes to a new size on that chart. Confirm the canvas resizes immediately, the status bar shows "Chart size updated", and about 2 seconds later shows a saved/ready status (confirming the auto-save timer fired).
4. Close and reopen the chart again. Confirm it opens at the manually-set size from step 3, not the fitted size from step 1.
5. Click "🔄 Reset" on that chart. Close and reopen it. Confirm it's back to being fit to the preview panel (Reset cleared the saved size).

- [ ] **Step 7: Commit**

```bash
git add pandaplot/gui/components/tabs/chart/chart_editor.py
git commit -m "Persist chart size and fit new charts to the preview panel"
```
