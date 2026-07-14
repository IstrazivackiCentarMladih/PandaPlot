# Chart Properties Panel & Persistence Bugfixes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix the chart properties panel's signal-feedback corruption bugs (tab-switch config clobbering, destructive Cancel, no-op Apply undo), the chart editor's crash on missing columns, and several smaller chart-command defects.

**Architecture:** Chart settings live on the `Chart` model (`config` dict + `DataSeries`/`FitData` dataclasses); the sidebar `ChartPropertiesPanel` edits the model live and publishes `CHART_UPDATED`; `ChartTab`/`ChartEditorWidget` re-render on that event. The fixes: (1) make programmatic control population signal-safe with a re-entrant `_updating_controls` guard, (2) introduce model-level snapshot/restore helpers and a "snapshot on load" baseline so Cancel reverts and Apply's undo actually works, (3) replace the crashing sample-data fallback with an explicit per-series resolution helper, and (4) delete the legacy `ChartConfiguration` dual-model path from the panel.

**Tech Stack:** Python 3.12, PySide6, matplotlib, pandas, pytest (no pytest-qt — tests must not instantiate widgets).

## Global Constraints

- Run tests with: `uv run pytest` (from repo root `c:\vso\PandaPlot`)
- Run the app for manual verification with: `uv run python -m pandaplot.app`
- Tests must NOT create Qt widgets or a `QApplication` (no pytest-qt in this repo). Test model functions, module-level helpers, and commands (with `unittest.mock.Mock` app contexts, following `tests/commands/project/note/test_create_note_command.py`).
- Do NOT delete `pandaplot/models/chart/chart_configuration.py` — its enums (`ChartType`, `LineStyleType`, `MarkerType`, `ScaleType`, `LegendPosition`) and dataclasses are used by the panel and by `tests/models/test_chart_line_style.py`.
- Out of scope (do not attempt): figure-size persistence / `fit_size_cm` wiring (covered by `docs/superpowers/plans/2026-07-12-chart-initial-size-fit-screen.md`), undo coverage for direct series edits, syncing panel title edits to the project tree.

---

### Task 1: Model-level chart snapshot/restore helpers

The snapshot logic currently lives as static methods on `ApplyChartPropertiesCommand`. The panel will also need it (Cancel, baseline-on-load), so move it to the model layer.

**Files:**
- Modify: `pandaplot/models/project/items/chart.py`
- Modify: `pandaplot/commands/project/chart/apply_chart_properties_command.py`
- Test: `tests/models/test_chart_snapshot.py`

**Interfaces:**
- Produces: `snapshot_chart_state(chart: Chart) -> Dict[str, Any]` and `restore_chart_state(chart: Chart, snapshot: Dict[str, Any]) -> None`, module-level functions in `pandaplot.models.project.items.chart`. Tasks 2 and 4 import these.

- [ ] **Step 1: Write the failing tests**

Create `tests/models/test_chart_snapshot.py`:

```python
"""Tests for model-level chart state snapshot/restore helpers."""

import numpy as np

from pandaplot.models.project.items.chart import (
    Chart,
    restore_chart_state,
    snapshot_chart_state,
)


def _make_chart():
    chart = Chart(name="My Chart")
    chart.add_data_series("ds1", "x", "y", label="s1", color="#112233")
    return chart


def test_restore_reverts_config_type_name_and_series():
    chart = _make_chart()
    snap = snapshot_chart_state(chart)

    chart.config["x_label"] = "changed"
    chart.chart_type = "scatter"
    chart.name = "Renamed"
    chart.data_series[0].color = "#ffffff"

    restore_chart_state(chart, snap)

    assert chart.config["x_label"] == ""
    assert chart.chart_type == "line"
    assert chart.name == "My Chart"
    assert chart.data_series[0].color == "#112233"


def test_snapshot_is_a_deep_copy_of_config():
    chart = _make_chart()
    snap = snapshot_chart_state(chart)
    chart.config["title"] = "mutated after snapshot"
    assert snap["config"]["title"] == "My Chart"


def test_restore_recreates_removed_series():
    chart = _make_chart()
    snap = snapshot_chart_state(chart)
    chart.data_series.clear()
    restore_chart_state(chart, snap)
    assert len(chart.data_series) == 1
    assert chart.data_series[0].label == "s1"


def test_restore_only_touches_fit_style_fields():
    chart = _make_chart()
    chart.add_fit_data(
        "ds1", "x", "y", "Linear",
        np.array([1.0]), np.array([2.0]),
        color="#ff0000", line_width=2.0,
    )
    snap = snapshot_chart_state(chart)

    chart.fit_data[0].color = "#00ff00"
    chart.fit_data[0].line_width = 5.0

    restore_chart_state(chart, snap)

    assert chart.fit_data[0].color == "#ff0000"
    assert chart.fit_data[0].line_width == 2.0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/models/test_chart_snapshot.py -v`
Expected: FAIL — `ImportError: cannot import name 'snapshot_chart_state'`

- [ ] **Step 3: Add the helpers to the chart model**

In `pandaplot/models/project/items/chart.py`, add to the imports at the top:

```python
import copy
from dataclasses import asdict, dataclass
```

(`dataclass` is already imported — extend that line with `asdict`; add `import copy`.)

Append at module level (after the `Chart` class):

```python
def snapshot_chart_state(chart: "Chart") -> Dict[str, Any]:
    """Capture the mutable chart state that the properties panel can change.

    Fit data x/y arrays are intentionally not snapshotted — only their
    editable style fields — because the arrays are immutable in the panel
    and can be large.
    """
    return {
        "config": copy.deepcopy(chart.config),
        "chart_type": chart.chart_type,
        "name": chart.name,
        "data_series": [asdict(s) for s in chart.data_series],
        "fit_data_styles": [
            {"color": f.color, "line_width": f.line_width}
            for f in chart.fit_data
        ],
    }


def restore_chart_state(chart: "Chart", snapshot: Dict[str, Any]) -> None:
    """Restore chart state captured by snapshot_chart_state."""
    chart.config = copy.deepcopy(snapshot["config"])
    chart.chart_type = snapshot["chart_type"]
    chart.name = snapshot["name"]
    chart.data_series = [DataSeries(**d) for d in snapshot["data_series"]]
    for i, fit_style in enumerate(snapshot["fit_data_styles"]):
        if i < len(chart.fit_data):
            chart.fit_data[i].color = fit_style["color"]
            chart.fit_data[i].line_width = fit_style["line_width"]
    chart.update_modified_time()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/models/test_chart_snapshot.py -v`
Expected: 4 PASS

- [ ] **Step 5: Make ApplyChartPropertiesCommand delegate to the helpers**

In `pandaplot/commands/project/chart/apply_chart_properties_command.py`:
- Delete the static methods `_snapshot_chart` and `_restore_snapshot` (lines 31-61) and the now-unused `import copy`, `from dataclasses import asdict`, and `DataSeries` import.
- Change the chart import to:

```python
from pandaplot.models.project.items.chart import (
    Chart,
    restore_chart_state,
    snapshot_chart_state,
)
```

- Replace call sites: `self._snapshot_chart(chart)` → `snapshot_chart_state(chart)` (2 places in `execute`), `self._restore_snapshot(chart, ...)` → `restore_chart_state(chart, ...)` (in `undo` and `redo`).

- [ ] **Step 6: Run the full test suite**

Run: `uv run pytest`
Expected: all PASS (no regressions)

- [ ] **Step 7: Commit**

```bash
git add pandaplot/models/project/items/chart.py pandaplot/commands/project/chart/apply_chart_properties_command.py tests/models/test_chart_snapshot.py
git commit -m "refactor: move chart snapshot/restore to model layer"
```

---

### Task 2: ApplyChartPropertiesCommand accepts a pre-captured baseline snapshot

The panel edits the chart live, so by the time Apply runs, the model already holds the new values — the command's "before" snapshot equals its "after" snapshot and undo is a no-op. Fix: let the caller pass the baseline captured when the chart was loaded into the panel.

**Files:**
- Modify: `pandaplot/commands/project/chart/apply_chart_properties_command.py`
- Create: `tests/commands/project/chart/__init__.py` (empty file)
- Test: `tests/commands/project/chart/test_apply_chart_properties_command.py`

**Interfaces:**
- Consumes: `snapshot_chart_state` / `restore_chart_state` from Task 1.
- Produces: `ApplyChartPropertiesCommand(app_context, chart_id: str, apply_fn: Callable[[Chart], None], old_snapshot: Optional[Dict[str, Any]] = None)`. Task 4 passes `old_snapshot`.

- [ ] **Step 1: Write the failing tests**

Create empty `tests/commands/project/chart/__init__.py`, then `tests/commands/project/chart/test_apply_chart_properties_command.py`:

```python
"""Tests for ApplyChartPropertiesCommand undo/redo with a pre-captured baseline."""

from unittest.mock import Mock

import pytest

from pandaplot.commands.project.chart import ApplyChartPropertiesCommand
from pandaplot.models.project.items.chart import Chart, snapshot_chart_state


@pytest.fixture
def app_context_with_chart():
    chart = Chart(name="Chart")
    chart.add_data_series("ds1", "x", "y", color="#112233")

    project = Mock()
    project.find_item.return_value = chart

    app_state = Mock()
    app_state.has_project = True
    app_state.current_project = project

    app_context = Mock()
    app_context.get_app_state.return_value = app_state
    app_context.event_bus = Mock()
    return app_context, chart


def test_undo_restores_provided_baseline_snapshot(app_context_with_chart):
    app_context, chart = app_context_with_chart
    baseline = snapshot_chart_state(chart)

    # Simulate the live edits the panel makes before Apply is clicked
    chart.config["x_label"] = "live edited"
    chart.data_series[0].color = "#ffffff"

    command = ApplyChartPropertiesCommand(
        app_context, chart.id, apply_fn=lambda c: None, old_snapshot=baseline)
    assert command.execute() is True

    command.undo()
    assert chart.config["x_label"] == ""
    assert chart.data_series[0].color == "#112233"


def test_redo_reapplies_the_edited_state(app_context_with_chart):
    app_context, chart = app_context_with_chart
    baseline = snapshot_chart_state(chart)
    chart.config["x_label"] = "live edited"

    command = ApplyChartPropertiesCommand(
        app_context, chart.id, apply_fn=lambda c: None, old_snapshot=baseline)
    command.execute()
    command.undo()
    command.redo()
    assert chart.config["x_label"] == "live edited"


def test_execute_without_baseline_snapshots_at_execute_time(app_context_with_chart):
    app_context, chart = app_context_with_chart

    def apply_fn(c):
        c.config["x_label"] = "applied"

    command = ApplyChartPropertiesCommand(app_context, chart.id, apply_fn=apply_fn)
    command.execute()

    command.undo()
    assert chart.config["x_label"] == ""
    command.redo()
    assert chart.config["x_label"] == "applied"
```

- [ ] **Step 2: Run tests to verify the new behavior fails**

Run: `uv run pytest tests/commands/project/chart/test_apply_chart_properties_command.py -v`
Expected: `test_undo_restores_provided_baseline_snapshot` and `test_redo_reapplies_the_edited_state` FAIL with `TypeError: ... unexpected keyword argument 'old_snapshot'`; the third test PASSES (existing behavior).

- [ ] **Step 3: Add the old_snapshot parameter**

In `apply_chart_properties_command.py`, change `__init__` and `execute`:

```python
    def __init__(self, app_context: AppContext, chart_id: str,
                 apply_fn: Callable[[Chart], None],
                 old_snapshot: Optional[Dict[str, Any]] = None):
        super().__init__()
        self.app_context = app_context
        self.chart_id = chart_id
        self._apply_fn = apply_fn
        # Baseline for undo. The panel edits the chart live, so the state at
        # execute() time already contains the user's changes; callers pass the
        # snapshot taken when the chart was loaded into the panel.
        self.old_snapshot: Optional[Dict[str, Any]] = old_snapshot
        self.new_snapshot: Optional[Dict[str, Any]] = None
```

```python
    @override
    def execute(self) -> bool:
        chart = self._find_chart()
        if not chart or not isinstance(chart, Chart):
            return False

        if self.old_snapshot is None:
            self.old_snapshot = snapshot_chart_state(chart)

        self._apply_fn(chart)
        self.new_snapshot = snapshot_chart_state(chart)

        self._emit_update(chart)
        return True
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/commands/project/chart/test_apply_chart_properties_command.py -v`
Expected: 3 PASS

- [ ] **Step 5: Commit**

```bash
git add pandaplot/commands/project/chart/apply_chart_properties_command.py tests/commands/project/chart/
git commit -m "fix: ApplyChartPropertiesCommand undo restores pre-edit baseline"
```

---

### Task 3: Guard programmatic control population in ChartPropertiesPanel

`load_chart_object` populates ~30 widgets without blocking signals; each `setText`/`setChecked`/`setValue` fires `_on_chart_config_changed`, which writes the **entire** config back from partially-stale controls. Because the loader reads later fields from the same `chart.config` it is clobbering, switching tabs between two charts silently copies the first chart's settings into the second. Fix with the existing `_updating_controls` flag, made re-entrant.

**Files:**
- Modify: `pandaplot/gui/components/sidebar/chart/chart_properties_panel.py`

**Interfaces:**
- Consumes: nothing from other tasks (independent).
- Produces: `load_chart_object` populates controls under `self._updating_controls`; `_load_series_into_controls` and `_load_fit_into_controls` save/restore the previous guard value instead of forcing it to `False`.

- [ ] **Step 1: Make the nested loaders re-entrant**

`_load_series_into_controls` (line ~1186) and `_load_fit_into_controls` (line ~1260) currently end with `finally: self._updating_controls = False`, which would clear an outer guard. In BOTH methods change the guard pattern from:

```python
        self._updating_controls = True
        try:
            ...
        finally:
            self._updating_controls = False
```

to:

```python
        previous_guard = self._updating_controls
        self._updating_controls = True
        try:
            ...
        finally:
            self._updating_controls = previous_guard
```

(Only the first and last lines change; the body stays as-is.)

- [ ] **Step 2: Wrap load_chart_object's populate block in the guard**

In `load_chart_object` (line ~1463), the `if chart:` branch currently runs `self._ensure_datasets_loaded()` then populates controls unguarded. Wrap everything in that branch from `self.title_edit.setText(...)` through `self.legend_show_frame_check.setChecked(...)` (the end of the branch) like this:

```python
        if chart:
            # Ensure datasets are available (important after opening a project file)
            self._ensure_datasets_loaded()

            # Populate controls without letting their change signals write
            # half-loaded values back into chart.config (that feedback loop
            # corrupted chart settings on every tab switch).
            previous_guard = self._updating_controls
            self._updating_controls = True
            try:
                # ... existing populate code, unchanged, indented one level ...
            finally:
                self._updating_controls = previous_guard
        else:
            ...
```

Note: `self.series_list.setCurrentRow(0)` inside this block triggers `_on_series_selection_changed` → `_load_series_into_controls`; with Step 1's re-entrant guard that nested call no longer drops the outer guard.

- [ ] **Step 3: Run the full test suite**

Run: `uv run pytest`
Expected: all PASS

- [ ] **Step 4: Manual verification**

Run: `uv run python -m pandaplot.app`
1. Create a project, import a CSV (File → Import or the welcome tab; sample CSVs exist in `tests/*.csv`), and create two charts from it (right-click the dataset in the project tree).
2. In chart A's properties panel set: X Label = "AAA", uncheck "Show Legend", Legend position = "lower left". Click Apply.
3. Switch to chart B's tab, then back to chart A's tab.
4. Verify: chart A still shows X Label "AAA" and legend hidden; chart B kept its own defaults (legend visible); the panel does NOT show "Modified *" right after a tab switch.

- [ ] **Step 5: Commit**

```bash
git add pandaplot/gui/components/sidebar/chart/chart_properties_panel.py
git commit -m "fix: guard chart panel control population against signal write-back"
```

---

### Task 4: Snapshot-on-load baseline; Cancel reverts; Apply gets a real undo

Cancel currently calls `load_chart(None)`, which loads *defaults into the widgets* and (before Task 3, via signals) wiped the chart's config; it never reverted the model. Fix: take a `snapshot_chart_state` baseline whenever a chart is loaded into the panel, restore it on Cancel, and pass it to `ApplyChartPropertiesCommand` on Apply.

**Files:**
- Modify: `pandaplot/gui/components/sidebar/chart/chart_properties_panel.py`

**Interfaces:**
- Consumes: `snapshot_chart_state` / `restore_chart_state` (Task 1), `old_snapshot` parameter (Task 2), guarded `load_chart_object` (Task 3).
- Produces: `self._loaded_snapshot: Optional[Dict[str, Any]]` panel attribute; `_on_reset` restores it.

- [ ] **Step 1: Add the import and the attribute**

Add to the imports in `chart_properties_panel.py`:

```python
from pandaplot.models.project.items.chart import restore_chart_state, snapshot_chart_state
```

In `__init__` (near `self._has_unsaved_changes: bool = False`, line ~132), add:

```python
        # Baseline for Cancel and for Apply's undo: the chart state as of the
        # last load into this panel or the last Apply.
        self._loaded_snapshot: Optional[dict] = None
```

- [ ] **Step 2: Capture the baseline in load_chart_object**

At the top of `load_chart_object`, right after `self.current_chart = chart`, add:

```python
        self._loaded_snapshot = snapshot_chart_state(chart) if chart else None
```

- [ ] **Step 3: Pass the baseline on Apply and refresh it**

Replace `_on_apply` (line ~1426):

```python
    def _on_apply(self):
        """Handle apply button click."""
        if not self.current_chart:
            return
        command = ApplyChartPropertiesCommand(
            self.app_context,
            chart_id=self.current_chart.id,
            apply_fn=self.apply_to_chart,
            old_snapshot=self._loaded_snapshot,
        )
        self.command_executor.execute_command(command)

        # The applied state is the new baseline for Cancel / the next Apply.
        self._loaded_snapshot = snapshot_chart_state(self.current_chart)
        self._has_unsaved_changes = False
        self._update_status_indicator()
```

- [ ] **Step 4: Make Cancel restore the baseline**

Replace `_on_reset` (line ~1439):

```python
    def _on_reset(self):
        """Revert live edits back to the last loaded/applied state."""
        if not self.current_chart or self._loaded_snapshot is None:
            return
        restore_chart_state(self.current_chart, self._loaded_snapshot)
        self.load_chart_object(self.current_chart)
        self.publish_event(ChartEvents.CHART_UPDATED, {
            "chart_id": self.current_chart.id,
            "update_type": "config_updated",
        })
```

(`load_chart_object` re-snapshots the restored chart, which is idempotent, and clears `_has_unsaved_changes`.)

- [ ] **Step 5: Run the full test suite**

Run: `uv run pytest`
Expected: all PASS

- [ ] **Step 6: Manual verification**

Run: `uv run python -m pandaplot.app`, open a project with a chart:
1. Change X Label to "temp" and toggle a grid checkbox — the preview updates live and status shows "Modified *".
2. Click **Cancel** → the widgets AND the chart preview revert to the pre-edit state; "Modified *" clears.
3. Change X Label to "kept", click **Apply**, then Edit → Undo → the label reverts to its pre-edit value in the preview. Edit → Redo → "kept" comes back.
4. Click Cancel after an Apply → nothing changes (baseline is the applied state).

- [ ] **Step 7: Commit**

```bash
git add pandaplot/gui/components/sidebar/chart/chart_properties_panel.py
git commit -m "fix: chart panel Cancel restores baseline; Apply undo works"
```

---

### Task 5: Remove the legacy ChartConfiguration path from the panel

`load_chart`, `_get_current_configuration`, `_load_configuration`, and `_load_default_configuration` form a dead parallel config model (`load_chart` even reads `current_project.charts`, which doesn't exist on `Project`). After Task 4, nothing routes through them. `ChartStyleManager` is only used by the panel.

**Files:**
- Modify: `pandaplot/gui/components/sidebar/chart/chart_properties_panel.py`
- Delete: `pandaplot/models/chart/chart_style_manager.py`
- Modify: `pandaplot/models/chart/__init__.py`

**Interfaces:**
- Consumes: Task 4 (Cancel no longer calls `load_chart`).
- Produces: `_clear_controls()` replaces `_load_default_configuration()` for the "no chart" case.

- [ ] **Step 1: Verify nothing else references the legacy pieces**

Run: `grep -rn "ChartStyleManager\|load_chart(\|_load_configuration\|_get_current_configuration\|_load_default_configuration\|current_chart_id" pandaplot/ tests/ --include="*.py"`
Expected: hits only inside `chart_properties_panel.py`, `chart_style_manager.py`, and `pandaplot/models/chart/__init__.py`. If anything else shows up, STOP and re-scope before deleting.

- [ ] **Step 2: Add a guarded control-clearing helper**

In `chart_properties_panel.py`, add this method (near `_reset_controls_for_series`):

```python
    def _clear_controls(self):
        """Reset panel controls to neutral defaults without touching any chart."""
        previous_guard = self._updating_controls
        self._updating_controls = True
        try:
            self.title_edit.clear()
            self.chart_type_combo.setCurrentIndex(0)
            self.x_label_edit.clear()
            self.y_label_edit.clear()
            self.x_grid_check.setChecked(True)
            self.y_grid_check.setChecked(True)
            self.x_auto_limits_check.setChecked(True)
            self.y_auto_limits_check.setChecked(True)
            self.legend_show_check.setChecked(True)
            self.legend_show_frame_check.setChecked(True)
            self.series_label_edit.clear()
        finally:
            self._updating_controls = previous_guard
```

- [ ] **Step 3: Delete the legacy code**

In `chart_properties_panel.py`:
- In `load_chart_object`'s `else:` branch, replace `self._load_default_configuration()` with `self._clear_controls()`.
- Delete methods: `load_chart`, `_get_current_configuration`, `_load_configuration`, `_load_default_configuration`.
- Delete `self.style_manager = ChartStyleManager()` and `self.current_chart_id: Optional[str] = None` from `__init__`.
- Delete the unused class-level signals `chart_created` / `chart_updated` (verify first: `grep -rn "chart_created\|chart_updated" pandaplot/ --include="*.py"` — expect no `.connect(` or `.emit(` hits on these panel signals).
- Prune imports: remove `ChartStyleManager`, and remove `ChartConfiguration`, `AxisStyle`, `LegendStyle`, `LineStyle`, `MarkerStyle` from the `chart_configuration` import if now unused (keep `ChartType`, `LineStyleType`, `MarkerType`, `ScaleType`, `LegendPosition`).

Delete the file `pandaplot/models/chart/chart_style_manager.py`, and in `pandaplot/models/chart/__init__.py` remove the `ChartStyleManager` import and its `__all__` entry.

- [ ] **Step 4: Run the full test suite**

Run: `uv run pytest`
Expected: all PASS (`tests/models/test_chart_line_style.py` still passes — it imports `chart_configuration`, not the style manager).

- [ ] **Step 5: Smoke-check the app starts and the panel works**

Run: `uv run python -m pandaplot.app` — open a chart tab, switch to a dataset tab (panel clears without errors), switch back.

- [ ] **Step 6: Commit**

```bash
git add -A pandaplot/models/chart/ pandaplot/gui/components/sidebar/chart/chart_properties_panel.py
git commit -m "refactor: remove legacy ChartConfiguration path from chart panel"
```

---

### Task 6: Replace the crashing sample-data fallback with per-series resolution

`generate_sample_data()` returns an **empty** DataFrame, but the missing-column/missing-dataset fallbacks in `update_chart` still do `self.sample_data["x"]` → `KeyError: 'x'` → the whole chart (valid series included) fails to render with "Chart error: 'x'". Replace with a testable helper that resolves each series or returns an error message; broken series are skipped and reported.

**Files:**
- Modify: `pandaplot/gui/components/tabs/chart/chart_editor.py`
- Test: `tests/gui/test_chart_editor_series_resolution.py`

**Interfaces:**
- Consumes: nothing from other tasks (independent).
- Produces: module-level `resolve_series_data(project, series) -> tuple` in `chart_editor.py` returning `(x_data, y_data, error)` where `error` is `None` on success, else a human-readable string and `x_data`/`y_data` are `None`.

- [ ] **Step 1: Write the failing tests**

Create `tests/gui/test_chart_editor_series_resolution.py` (module import is safe without QApplication — see `tests/gui/test_chart_editor_tick_helpers.py` for precedent):

```python
"""Tests for resolve_series_data (no Qt widgets involved)."""

import pandas as pd

from pandaplot.gui.components.tabs.chart.chart_editor import resolve_series_data
from pandaplot.models.project.items.chart import DataSeries
from pandaplot.models.project.items.dataset import Dataset
from pandaplot.models.project.project import Project


def _project_with_dataset():
    project = Project("P")
    dataset = Dataset(name="ds", data=pd.DataFrame({"a": [1, 2], "b": [3, 4]}))
    project.add_item(dataset)
    return project, dataset


def test_resolves_x_and_y_columns():
    project, dataset = _project_with_dataset()
    series = DataSeries(dataset_id=dataset.id, x_column="a", y_column="b")
    x, y, error = resolve_series_data(project, series)
    assert error is None
    assert list(x) == [1, 2]
    assert list(y) == [3, 4]


def test_empty_x_column_uses_dataframe_index():
    project, dataset = _project_with_dataset()
    series = DataSeries(dataset_id=dataset.id, x_column="", y_column="b")
    x, y, error = resolve_series_data(project, series)
    assert error is None
    assert list(x) == [0, 1]


def test_missing_dataset_returns_error():
    project, _ = _project_with_dataset()
    series = DataSeries(dataset_id="nope", x_column="a", y_column="b")
    x, y, error = resolve_series_data(project, series)
    assert x is None and y is None
    assert "nope" in error


def test_missing_column_returns_error_naming_the_column():
    project, dataset = _project_with_dataset()
    series = DataSeries(dataset_id=dataset.id, x_column="a", y_column="gone")
    x, y, error = resolve_series_data(project, series)
    assert x is None and y is None
    assert "gone" in error


def test_no_project_returns_error():
    series = DataSeries(dataset_id="ds", x_column="a", y_column="b")
    x, y, error = resolve_series_data(None, series)
    assert error is not None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/gui/test_chart_editor_series_resolution.py -v`
Expected: FAIL — `ImportError: cannot import name 'resolve_series_data'`

- [ ] **Step 3: Implement the helper**

In `chart_editor.py`, add at module level (next to `apply_axis_ticks`):

```python
def resolve_series_data(project, series):
    """Resolve a DataSeries against the project's datasets.

    Returns (x_data, y_data, None) on success, or (None, None, message)
    when the dataset or a column can't be found. An empty x_column means
    "plot against the DataFrame index".
    """
    from pandaplot.models.project.items.dataset import Dataset

    if project is None:
        return None, None, "no project loaded"

    dataset = project.find_item(series.dataset_id)
    if not isinstance(dataset, Dataset) or dataset.data is None:
        return None, None, f"dataset '{series.dataset_id}' not found"

    df = dataset.data
    if not series.y_column:
        return None, None, "no Y column configured"

    missing = [c for c in (series.x_column, series.y_column)
               if c and c not in df.columns]
    if missing:
        cols = ", ".join(f"'{c}'" for c in missing)
        return None, None, f"column {cols} not found in '{dataset.name}'"

    x_data = df[series.x_column] if series.x_column else df.index
    return x_data, df[series.y_column], None
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/gui/test_chart_editor_series_resolution.py -v`
Expected: 5 PASS

- [ ] **Step 5: Rewrite the data-plotting section of update_chart**

In `update_chart` (chart_editor.py), replace the entire series-plotting block — from `if not self.chart.data_series:` (line ~437) down to (but not including) the `# Plot fit data from chart.fit_data` loop (line ~532) — with:

```python
            series_errors = []
            if not self.chart.data_series:
                self.dataset_label.setText("No Data Loaded")
            else:
                project = self.app_context.get_app_state().current_project
                for i, series in enumerate(self.chart.data_series):
                    x_data, y_data, error = resolve_series_data(project, series)
                    if error:
                        series_errors.append(
                            f"{series.label or f'Series {i + 1}'}: {error}")
                        continue

                    alpha = series.alpha if series.visible else 0.3
                    if self.chart.chart_type == "line":
                        mfc = series.marker_color or series.color
                        mec = series.marker_edge_color or series.color
                        self.chart_canvas.axes.plot(x_data, y_data,
                                                    color=series.color,
                                                    linewidth=series.line_width,
                                                    linestyle=_linestyle_map.get(series.line_style, "-"),
                                                    marker=_marker_map.get(series.marker_style, "o"),
                                                    markersize=series.marker_size,
                                                    markerfacecolor=mfc,
                                                    markeredgecolor=mec,
                                                    label=series.label,
                                                    alpha=alpha)
                    elif self.chart.chart_type == "scatter":
                        mfc = series.marker_color or series.color
                        mec = series.marker_edge_color or series.color
                        self.chart_canvas.axes.scatter(x_data, y_data,
                                                       c=mfc,
                                                       edgecolors=mec,
                                                       marker=_marker_map.get(series.marker_style, "o"),
                                                       s=series.marker_size * 10,
                                                       label=series.label,
                                                       alpha=alpha)
                    elif self.chart.chart_type == "bar":
                        self.chart_canvas.axes.bar(x_data, y_data,
                                                   color=series.color,
                                                   label=series.label,
                                                   alpha=alpha)
                    elif self.chart.chart_type == "hist":
                        self.chart_canvas.axes.hist(y_data, bins=20,
                                                    color=series.color,
                                                    label=series.label,
                                                    alpha=alpha)
```

Then, at the very end of the `try:` block in `update_chart` (right after `self.chart_canvas.draw()`), add:

```python
            if series_errors:
                self.update_status("Skipped: " + "; ".join(series_errors))
            else:
                self.update_status("Ready")
```

- [ ] **Step 6: Remove the dead sample-data code**

In `chart_editor.py` delete:
- `self.sample_data = self.generate_sample_data()` in `__init__` (and its TODO comment)
- the `generate_sample_data` method
- the now-unused `import pandas as pd` at the top (verify with a grep in the file first)

- [ ] **Step 7: Run the full test suite**

Run: `uv run pytest`
Expected: all PASS

- [ ] **Step 8: Manual verification**

Run: `uv run python -m pandaplot.app`:
1. Chart with valid series → renders normally, status "Ready".
2. Delete/rename a column the chart uses (dataset tab → column context menu) → chart re-renders the remaining valid series; status shows `Skipped: <label>: column 'x' not found in 'ds'` instead of the old "Chart error: 'x'".

- [ ] **Step 9: Commit**

```bash
git add pandaplot/gui/components/tabs/chart/chart_editor.py tests/gui/test_chart_editor_series_resolution.py
git commit -m "fix: skip and report unresolvable chart series instead of crashing render"
```

---

### Task 7: Remove the editor's Save button and dead auto-save; give menu Save the Ctrl+S shortcut

The 💾 Save action only bumps `modified_time` and shows "Saved ✓" — nothing reaches disk; real saving is File → Save (SaveProjectCommand). The `auto_save_timer` is never started and `is_modified` is never set `True` (the pattern was copied from `note_editor.py` where it *is* wired). Remove the button and the dead code. Note: the editor's action was the app's only Ctrl+S binding — the File menu's Save action has no shortcut — so move the standard Save shortcut to the menu action.

**Files:**
- Modify: `pandaplot/gui/components/tabs/chart/chart_editor.py`
- Modify: `pandaplot/gui/components/main_menu/main_menu.py`

**Interfaces:**
- Consumes: nothing from other tasks (independent).
- Produces: `save_chart`, `auto_save`, `auto_save_timer`, `is_modified` no longer exist on `ChartEditorWidget`.

- [ ] **Step 1: Delete the Save action and dead auto-save machinery**

In `ChartEditorWidget.__init__`, delete:

```python
        self.is_modified = False
        self.auto_save_timer = QTimer()
        self.auto_save_timer.timeout.connect(self.auto_save)
        self.auto_save_timer.setSingleShot(True)
```

In `create_chart_toolbar_actions`, delete the Save action block:

```python
        # Save chart action
        save_action = QAction("💾 Save", self)
        save_action.setShortcut(QKeySequence.StandardKey.Save)
        save_action.triggered.connect(self.save_chart)
        toolbar.addAction(save_action)
```

Delete the `save_chart` and `auto_save` methods entirely. Remove `QKeySequence` from the `PySide6.QtGui` import if now unused in the file (verify with grep first; `QAction` is still used by the remaining toolbar actions).

- [ ] **Step 2: Add the standard Save shortcut to the File menu action**

In `pandaplot/gui/components/main_menu/main_menu.py`, the Save action (line ~145) has no shortcut. Add one, matching the style of the existing undo/redo actions:

```python
        save_action = QAction("Save", self)
        save_action.setShortcut(QKeySequence.StandardKey.Save)
        save_action.triggered.connect(lambda: self.app_context.get_command_executor(
        ).execute_command(SaveProjectCommand(self.app_context)))
        file_menu.addAction(save_action)
```

(Only the `setShortcut` line is new; `QKeySequence` is already imported in this file.)

- [ ] **Step 3: Run the full test suite**

Run: `uv run pytest`
Expected: all PASS

- [ ] **Step 4: Manual verification**

Run: `uv run python -m pandaplot.app`:
1. Open a chart tab → the preview toolbar shows only 🔄 Reset and 🔍 Reset Zoom (no 💾 Save), plus the matplotlib nav toolbar.
2. Press Ctrl+S anywhere → the project save runs (save dialog for a new project, or the `.pplot` file's mtime updates).
3. File → Save shows "Ctrl+S" next to the menu entry.

- [ ] **Step 5: Commit**

```bash
git add pandaplot/gui/components/tabs/chart/chart_editor.py pandaplot/gui/components/main_menu/main_menu.py
git commit -m "refactor: remove chart editor save button; bind Ctrl+S to project save"
```

---

### Task 8: CreateChartCommand.redo reuses the created chart

`redo()` calls `execute()`, which builds a brand-new `Chart` with a new id — after undo/redo, any open references and the command's own snapshot history point at a dead id.

**Files:**
- Modify: `pandaplot/commands/project/chart/create_chart_command.py`
- Test: `tests/commands/project/chart/test_create_chart_command.py`

**Interfaces:**
- Consumes: test package `tests/commands/project/chart/` from Task 2.
- Produces: `self.created_chart: Optional[Chart]` attribute; `redo()` re-adds the same instance.

- [ ] **Step 1: Write the failing test**

Create `tests/commands/project/chart/test_create_chart_command.py`:

```python
"""Tests for CreateChartCommand undo/redo identity."""

from unittest.mock import Mock

import pytest

from pandaplot.commands.project.chart import CreateChartCommand


@pytest.fixture
def app_context_with_project():
    dataset = Mock()
    dataset.name = "ds"
    dataset.data = None  # skip default-series creation

    project = Mock()
    project.find_item.return_value = dataset

    app_state = Mock()
    app_state.has_project = True
    app_state.current_project = project

    app_context = Mock()
    app_context.get_app_state.return_value = app_state
    app_context.get_ui_controller.return_value = Mock()
    app_context.event_bus = Mock()
    return app_context, project


def test_redo_readds_the_same_chart_instance(app_context_with_project):
    app_context, project = app_context_with_project
    command = CreateChartCommand(app_context, dataset_id="ds-1", chart_name="C")

    assert command.execute() is True
    first_id = command.created_chart_id
    first_chart = project.add_item.call_args[0][0]

    command.undo()
    project.remove_item_by_id.assert_called_once_with(first_id)

    command.redo()
    redo_chart = project.add_item.call_args[0][0]
    assert redo_chart is first_chart
    assert command.created_chart_id == first_id
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `uv run pytest tests/commands/project/chart/test_create_chart_command.py -v`
Expected: FAIL — `assert redo_chart is first_chart` (redo built a new Chart)

- [ ] **Step 3: Store the chart and re-add it on redo**

In `create_chart_command.py`:
- In `__init__`, add `self.created_chart: Optional[Chart] = None` next to `self.created_chart_id`.
- In `execute`, right after `self.created_chart_id = chart.id`, add `self.created_chart = chart`.
- Replace `redo`:

```python
    @override
    def redo(self):
        """Redo the chart creation, re-adding the original chart instance."""
        if self.created_chart is None:
            self.execute()
            return

        app_state = self.app_context.get_app_state()
        if not app_state.has_project or not app_state.current_project:
            return
        project = app_state.current_project

        project.add_item(self.created_chart, parent_id=self.parent_id)
        self.created_chart_id = self.created_chart.id

        self.app_context.event_bus.emit(ChartEvents.CHART_CREATED, ChartCreatedData(
            chart_id=self.created_chart.id
        ).to_dict())
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/commands/project/chart/ -v`
Expected: all PASS

- [ ] **Step 5: Commit**

```bash
git add pandaplot/commands/project/chart/create_chart_command.py tests/commands/project/chart/test_create_chart_command.py
git commit -m "fix: CreateChartCommand.redo reuses the original chart instance and id"
```

---

### Task 9: Hide unimplemented chart types from the panel

`box` and `violin` are selectable in the chart-type combo but `update_chart` has no rendering branch for them — selecting one silently blanks the chart.

**Files:**
- Modify: `pandaplot/gui/components/sidebar/chart/chart_properties_panel.py`

**Interfaces:**
- Consumes: nothing.
- Produces: module-level `IMPLEMENTED_CHART_TYPES` list in `chart_properties_panel.py`.

- [ ] **Step 1: Restrict the combo to implemented types**

In `chart_properties_panel.py`, add at module level (after the imports):

```python
# Only chart types that ChartEditorWidget.update_chart can actually render.
# BOX and VIOLIN exist in the enum but have no rendering branch yet.
IMPLEMENTED_CHART_TYPES = [
    ChartType.LINE,
    ChartType.SCATTER,
    ChartType.BAR,
    ChartType.HISTOGRAM,
]
```

In `_create_chart_info_section`, change the combo population from:

```python
        for chart_type in ChartType:
            self.chart_type_combo.addItem(chart_type.value.title(), chart_type)
```

to:

```python
        for chart_type in IMPLEMENTED_CHART_TYPES:
            self.chart_type_combo.addItem(chart_type.value.title(), chart_type)
```

Also remove the `ChartType.BOX` / `ChartType.VIOLIN` entries from the two `chart_type_map` dicts in this file (`_on_chart_config_changed` and `apply_to_chart`) and from the reverse map in `load_chart_object`.

- [ ] **Step 2: Run the full test suite and smoke-check**

Run: `uv run pytest` — all PASS.
Run: `uv run python -m pandaplot.app` — the chart-type combo shows only Line / Scatter / Bar / Histogram; each renders.

- [ ] **Step 3: Commit**

```bash
git add pandaplot/gui/components/sidebar/chart/chart_properties_panel.py
git commit -m "fix: hide unimplemented box/violin chart types from the panel"
```
