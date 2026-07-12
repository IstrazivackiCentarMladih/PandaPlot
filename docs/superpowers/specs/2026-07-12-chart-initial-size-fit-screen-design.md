# Chart Initial Size: Fit the Preview Panel Unless Saved

## Problem

The chart editor's preview size (width/height in cm, via `width_spin`/`height_spin` in
`pandaplot/gui/components/tabs/chart/chart_editor.py`) is currently hardcoded to 20×15cm on
every open and is never persisted — confirmed by the prior cm-units plan, which explicitly
scoped persistence out ("Sizing stays session-only ... matches current behavior, no scope
change here"). Two problems follow from that:

- A chart that's much smaller or larger than 20×15cm always opens at the wrong size and has
  to be manually resized every single time.
- There's no way to set a chart's preferred size once and have it stick.

## Goal

1. When a chart has no previously-saved size, size it on open to fit the visible preview
   panel (the scrollable canvas area), so it opens without needing scrollbars or manual
   resizing.
2. When a chart *does* have a saved size (because the user resized it before, or because a
   fit-to-panel size was already computed for it once), always reopen at that saved size —
   never re-fit.
3. Persist `width_cm`/`height_cm` per chart in `chart.config`, using the existing (currently
   unused) auto-save machinery (`is_modified` + `auto_save_timer`).
4. Loosen the spinbox minimums from 10cm/8cm down to 2cm/2cm width/height, so small charts
   are actually reachable.

## Non-goals

- Any project-file migration. `width_cm`/`height_cm` are read with `.get(key, None)`; charts
  saved before this change simply have no saved size and fit-to-panel on next open, same as
  a brand-new chart.
- Changing the cm↔inches conversion, DPI handling, or scroll/resize mechanics established in
  the prior cm-units plan — this only adds persistence and an initial-fit computation on top
  of that existing plumbing.
- Re-fitting an already-sized chart if the window/panel is later resized. Saved size is
  sticky; fit-to-panel only ever applies once, the first time a chart is opened with no
  saved size.

## Design

### 1. Data model: no new defaults in `_init_default_config`

**File:** `pandaplot/models/project/items/chart.py`

Deliberately *not* adding `width_cm`/`height_cm` to `Chart._init_default_config()`. Their
absence from `chart.config` is exactly the signal "no saved size yet, fit to panel." This
also means `reset_chart()` (which calls `_init_default_config()`) naturally clears any saved
size back to "unset," so Reset also resets the chart back to fit-to-panel behavior — no extra
code needed for that.

### 2. Spinbox range

**File:** `pandaplot/gui/components/tabs/chart/chart_editor.py`,
`create_chart_preview_section`

Change `width_spin.setRange(10, 50)` → `setRange(2, 50)` and `height_spin.setRange(8, 40)` →
`setRange(2, 40)`. Initial constructed values stay 20/15 as a neutral placeholder — they get
overwritten by `load_chart_config()` immediately after construction, before the user ever
sees them (see below).

### 3. Two distinct code paths: apply-silently vs. apply-and-persist

Today `_on_size_changed` (connected to `valueChanged`) both resizes the canvas and (after
this change) persists + marks modified. That's correct for interactive user drags, but wrong
for loading a saved size — reloading a chart shouldn't flag it "modified." So the resize
mechanics are split out into a shared helper:

```python
def _resize_canvas(self, width_cm, height_cm):
    """Resize the canvas to the given size, without touching chart.config or is_modified."""
    self.chart_canvas.set_size(cm_to_inches(width_cm), cm_to_inches(height_cm))
```

`_on_size_changed` (still connected to both spinboxes' `valueChanged`) becomes:

```python
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

        QTimer.singleShot(2000, lambda: self.update_status("Ready"))
```

(`auto_save_timer.start(2000)` — a 2s debounce matching the existing single-shot timer setup
in `__init__`; the timer already exists and is already wired to call `auto_save()`, which
only acts `if self.is_modified`, so this is just actually starting it, which nothing
currently does.)

### 4. Loading: use saved size, or defer to fit-to-panel

**File:** `pandaplot/gui/components/tabs/chart/chart_editor.py`, `load_chart_config`

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
```

The `blockSignals` pair prevents `setValue` from firing `_on_size_changed` (which would
mark the chart modified merely for reopening it at the size it was already saved at).

### 5. Fit-to-panel computation

**File:** `pandaplot/gui/components/tabs/chart/chart_editor.py`, new method

```python
def _fit_size_to_preview_panel(self):
    """Compute an initial chart size that fits the visible preview panel, for a
    chart that has never had a size saved. Applies via the normal size-changed
    path so the computed size is persisted and won't need refitting next time."""
    if not isValid(self.chart_canvas):
        return
    viewport = self.canvas_scroll.viewport()
    dpi = self.chart_canvas.fig.dpi
    width_cm = inches_to_cm(viewport.width() / dpi)
    height_cm = inches_to_cm(viewport.height() / dpi)
    self.width_spin.setValue(round(width_cm))
    self.height_spin.setValue(round(height_cm))
```

`setValue` here is *not* signal-blocked — letting it fire `_on_size_changed` naturally
applies the fitted size to the canvas and, per the design goal, persists it into
`chart.config` immediately so subsequent opens reuse it rather than re-fitting. `setValue`
also clamps to the spinbox's `[2, 50]`/`[2, 40]` range on its own, so no separate clamping
code is needed. `canvas_scroll` (currently a local variable in
`create_chart_preview_section`) becomes `self.canvas_scroll` so this method can reach it.

`inches_to_cm` is already imported-adjacent (`cm_to_inches` is imported from
`chart_canvas.py` today); add `inches_to_cm` to that same import line.

The 100ms delay mirrors the existing `QTimer.singleShot(100, self._apply_theme)` pattern
already used in `__init__` for "wait for the widget layout to settle" — same rationale
applies here, since `viewport()` doesn't have its final size until after the widget is shown
and laid out.

### 6. Ordering recap

`__init__` already calls `self._initialize()` (builds UI, constructs `chart_canvas` at a
placeholder 20×15cm) then `self.load_chart_config()` then `self.update_chart()`. No change to
that ordering — `load_chart_config()` is where the saved-size-or-fit branch now lives.

## Testing

No pytest-qt in this repo (per the prior cm-units plan's stated convention), so this is
verified by code review plus a manual checklist, consistent with how the scrollable-canvas
work was verified:

1. Open a chart that has never been resized (no `width_cm`/`height_cm` in its config).
   Confirm it opens sized to fill the preview panel with no scrollbars, and that the
   spinboxes reflect the fitted cm values (not 20/15).
2. Close and reopen that same chart. Confirm it now opens at the *previously fitted* size
   (not re-fit to a possibly-different panel size), i.e. the fit only happened once.
3. Manually drag the width/height spinboxes to a new size. Confirm the canvas resizes and,
   after ~2s, the status reflects a save (consistent with existing auto-save status
   behavior). Reopen the chart and confirm the new size persisted.
4. Confirm the spinboxes now allow values down to 2cm on both axes.
5. Click "🔄 Reset" on a chart with a saved size. Confirm the next reopen (or an
   immediately-following fit check) treats it as unsized again — i.e. Reset clears the saved
   size back to fit-to-panel.
