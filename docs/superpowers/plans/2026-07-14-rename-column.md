# Rename Column Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rename a dataset column from the table's header context menu, cascading the rename to chart series and fit references in one undoable step.

**Architecture:** A new `RenameColumnCommand` (mirroring `ChangeColumnDtypeCommand`'s validation style) renames the DataFrame column, walks the project's charts to update name-based references (`DataSeries.x_column/y_column`, `FitData.source_x_column/source_y_column`), and emits the existing-but-unused `DatasetOperationEvents.DATASET_COLUMN_RENAMED` event plus `CHART_UPDATED` per affected chart. UI is a "Rename column..." context-menu action opening a `QInputDialog`; the table model refreshes headers on the rename event.

**Tech Stack:** Python 3.12, PySide6, pandas, pytest (no pytest-qt).

**Spec:** `docs/superpowers/specs/2026-07-14-rename-column-design.md`

## Global Constraints

- Run tests with `uv run pytest` from repo root `c:\vso\PandaPlot`.
- Tests must NOT create Qt widgets or a `QApplication`; command tests use real `Project`/`Dataset`/`Chart` models with a `unittest.mock.Mock` app context (pattern: `tests/commands/project/note/test_create_note_command.py`).
- Undo/redo must be a single step: DataFrame rename and reference cascade happen together.
- Series/fit **labels are never modified** — only `x_column`/`y_column`/`source_x_column`/`source_y_column` fields.
- Reference matching requires BOTH the dataset id AND the old column name; same-named columns in other datasets stay untouched.
- `CHART_UPDATED` events must carry a `"chart"` key (this triggers the properties panel's full resync).

---

### Task 1: RenameColumnCommand with chart-reference cascade

**Files:**
- Create: `pandaplot/commands/project/dataset/rename_column_command.py`
- Modify: `pandaplot/models/events/event_data.py` (add `DatasetColumnRenamedData` next to `DatasetColumnsRemovedData`)
- Test: `tests/commands/project/dataset/test_rename_column_command.py`

**Interfaces:**
- Consumes: existing `DatasetOperationEvents.DATASET_COLUMN_RENAMED` constant (`pandaplot/models/events/event_types.py:60`), `ChartEvents.CHART_UPDATED`, `EventData` base (`to_dict`/`from_dict`).
- Produces: `RenameColumnCommand(app_context, dataset_id: str, column_index: int, new_name: str)` and frozen dataclass `DatasetColumnRenamedData(dataset_id: str, column_index: int, old_name: str, new_name: str)`. Task 2 uses both.

- [ ] **Step 1: Add the event payload dataclass**

In `pandaplot/models/events/event_data.py`, after `DatasetColumnsRemovedData`, add:

```python
@dataclass(frozen=True)
class DatasetColumnRenamedData(EventData):
    dataset_id: str
    column_index: int
    old_name: str
    new_name: str
```

- [ ] **Step 2: Write the failing tests**

Create `tests/commands/project/dataset/test_rename_column_command.py`:

```python
"""Tests for RenameColumnCommand (DataFrame rename + chart-reference cascade)."""

from unittest.mock import Mock

import numpy as np
import pandas as pd
import pytest

from pandaplot.commands.project.dataset.rename_column_command import RenameColumnCommand
from pandaplot.models.events.event_types import ChartEvents, DatasetOperationEvents
from pandaplot.models.project import Project
from pandaplot.models.project.items import Chart, Dataset


@pytest.fixture
def env():
    project = Project("P")
    dataset = Dataset(name="ds", data=pd.DataFrame({"a": [1, 2], "b": [3, 4]}))
    other = Dataset(name="other", data=pd.DataFrame({"a": [5]}))
    project.add_item(dataset)
    project.add_item(other)

    chart = Chart(name="c")
    chart.add_data_series(dataset.id, "a", "b", label="s1")
    chart.add_data_series(other.id, "a", "a", label="s2")  # other dataset: must not change
    chart.add_fit_data(dataset.id, "a", "b", "Linear",
                       np.array([1.0]), np.array([2.0]))
    project.add_item(chart)

    untouched_chart = Chart(name="c2")
    untouched_chart.add_data_series(other.id, "a", "a", label="s3")
    project.add_item(untouched_chart)

    app_state = Mock()
    app_state.has_project = True
    app_state.current_project = project
    app_context = Mock()
    app_context.get_app_state.return_value = app_state
    app_context.get_ui_controller.return_value = Mock()
    app_context.event_bus = Mock()
    return app_context, dataset, other, chart


def _chart_updated_calls(app_context):
    return [c for c in app_context.event_bus.emit.call_args_list
            if c.args[0] == ChartEvents.CHART_UPDATED]


def test_rename_updates_dataframe_and_matching_references(env):
    app_context, dataset, other, chart = env
    command = RenameColumnCommand(app_context, dataset.id, 0, "time")

    assert command.execute() is True
    assert list(dataset.data.columns) == ["time", "b"]
    assert chart.data_series[0].x_column == "time"
    assert chart.data_series[0].y_column == "b"
    assert chart.fit_data[0].source_x_column == "time"
    # same column name in another dataset: untouched
    assert chart.data_series[1].x_column == "a"
    assert list(other.data.columns) == ["a"]


def test_undo_and_redo_round_trip(env):
    app_context, dataset, _, chart = env
    command = RenameColumnCommand(app_context, dataset.id, 0, "time")
    command.execute()

    command.undo()
    assert list(dataset.data.columns) == ["a", "b"]
    assert chart.data_series[0].x_column == "a"
    assert chart.fit_data[0].source_x_column == "a"

    command.redo()
    assert list(dataset.data.columns) == ["time", "b"]
    assert chart.data_series[0].x_column == "time"


def test_duplicate_name_rejected(env):
    app_context, dataset, _, _ = env
    command = RenameColumnCommand(app_context, dataset.id, 0, "b")
    assert command.execute() is False
    assert list(dataset.data.columns) == ["a", "b"]
    app_context.get_ui_controller.return_value.show_error_message.assert_called_once()


def test_empty_name_rejected(env):
    app_context, dataset, _, _ = env
    command = RenameColumnCommand(app_context, dataset.id, 0, "   ")
    assert command.execute() is False
    assert list(dataset.data.columns) == ["a", "b"]


def test_unchanged_name_is_silent_noop(env):
    app_context, dataset, _, _ = env
    command = RenameColumnCommand(app_context, dataset.id, 0, "a")
    assert command.execute() is False
    assert list(dataset.data.columns) == ["a", "b"]
    app_context.get_ui_controller.return_value.show_error_message.assert_not_called()


def test_events_emitted_only_for_affected_charts(env):
    app_context, dataset, _, chart = env
    command = RenameColumnCommand(app_context, dataset.id, 0, "time")
    command.execute()

    renamed_calls = [c for c in app_context.event_bus.emit.call_args_list
                     if c.args[0] == DatasetOperationEvents.DATASET_COLUMN_RENAMED]
    assert len(renamed_calls) == 1
    assert renamed_calls[0].args[1]["old_name"] == "a"
    assert renamed_calls[0].args[1]["new_name"] == "time"

    updated = _chart_updated_calls(app_context)
    assert len(updated) == 1  # 'untouched_chart' gets no event
    assert updated[0].args[1]["chart_id"] == chart.id
    assert "chart" in updated[0].args[1]
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `uv run pytest tests/commands/project/dataset/test_rename_column_command.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'pandaplot.commands.project.dataset.rename_column_command'`

- [ ] **Step 4: Implement the command**

Create `pandaplot/commands/project/dataset/rename_column_command.py`:

```python
"""Command for renaming a dataset column, cascading to chart/fit references."""

from typing import List, Optional, override

from pandaplot.commands.base_command import Command
from pandaplot.gui.controllers.ui_controller import UIController
from pandaplot.models.events.event_data import DatasetColumnRenamedData
from pandaplot.models.events.event_types import ChartEvents, DatasetOperationEvents
from pandaplot.models.project.items import Chart, Dataset
from pandaplot.models.state.app_context import AppContext
from pandaplot.models.state.app_state import AppState


class RenameColumnCommand(Command):
    """Rename a dataset column and update chart/fit references to it.

    The DataFrame rename and the reference cascade are one undoable step;
    series/fit labels are user-editable text and are never modified.
    """

    def __init__(self, app_context: AppContext, dataset_id: str,
                 column_index: int, new_name: str):
        super().__init__()
        self.app_context = app_context
        self.app_state: AppState = app_context.get_app_state()
        self.ui_controller: UIController = app_context.get_ui_controller()

        self.dataset_id = dataset_id
        self.column_index = column_index
        self.new_name = new_name.strip()
        self.old_name: Optional[str] = None
        self.dataset: Optional[Dataset] = None

    @override
    def execute(self) -> bool:
        try:
            if not self.app_state.has_project or not self.app_state.current_project:
                self.ui_controller.show_warning_message(
                    "Rename Column", "Please open or create a project first.")
                return False
            project = self.app_state.current_project

            found_item = project.find_item(self.dataset_id)
            if not isinstance(found_item, Dataset) or found_item.data is None:
                self.ui_controller.show_error_message(
                    "Rename Column", f"Dataset with ID '{self.dataset_id}' not found.")
                return False
            self.dataset = found_item

            columns = list(self.dataset.data.columns)
            if not (0 <= self.column_index < len(columns)):
                self.ui_controller.show_error_message(
                    "Rename Column", f"Column index {self.column_index} is out of range.")
                return False

            self.old_name = columns[self.column_index]
            if not self.new_name:
                self.ui_controller.show_error_message(
                    "Rename Column", "Column name cannot be empty.")
                return False
            if self.new_name == self.old_name:
                return False
            if self.new_name in columns:
                self.ui_controller.show_error_message(
                    "Rename Column",
                    f"A column named '{self.new_name}' already exists in this dataset.")
                return False

            self._apply_rename(self.old_name, self.new_name)
            return True

        except Exception as e:
            error_msg = f"Failed to rename column: {e}"
            self.logger.error(error_msg, exc_info=True)
            self.ui_controller.show_error_message("Rename Column Error", error_msg)
            return False

    def _apply_rename(self, from_name: str, to_name: str) -> None:
        """Rename the DataFrame column, cascade references, emit events."""
        if self.dataset is None or self.dataset.data is None:
            return
        self.dataset.data.rename(columns={from_name: to_name}, inplace=True)
        self.dataset.update_modified_time()

        affected_charts = self._update_chart_references(from_name, to_name)

        self.app_context.event_bus.emit(
            DatasetOperationEvents.DATASET_COLUMN_RENAMED,
            DatasetColumnRenamedData(
                dataset_id=self.dataset_id,
                column_index=self.column_index,
                old_name=from_name,
                new_name=to_name,
            ).to_dict())
        for chart in affected_charts:
            self.app_context.event_bus.emit(ChartEvents.CHART_UPDATED, {
                "chart_id": chart.id,
                "chart": chart,
            })

    def _update_chart_references(self, from_name: str, to_name: str) -> List[Chart]:
        """Point series/fits of this dataset at the new name; return affected charts."""
        project = self.app_state.current_project
        if not project:
            return []
        affected: List[Chart] = []
        for item in project.get_all_items():
            if not isinstance(item, Chart):
                continue
            changed = False
            for series in item.data_series:
                if series.dataset_id != self.dataset_id:
                    continue
                if series.x_column == from_name:
                    series.x_column = to_name
                    changed = True
                if series.y_column == from_name:
                    series.y_column = to_name
                    changed = True
            for fit in item.fit_data:
                if fit.source_dataset_id != self.dataset_id:
                    continue
                if fit.source_x_column == from_name:
                    fit.source_x_column = to_name
                    changed = True
                if fit.source_y_column == from_name:
                    fit.source_y_column = to_name
                    changed = True
            if changed:
                item.update_modified_time()
                affected.append(item)
        return affected

    @override
    def undo(self):
        """Rename back and restore references (same walk, names swapped)."""
        if self.old_name:
            self._apply_rename(self.new_name, self.old_name)

    @override
    def redo(self):
        """Re-apply the rename and reference cascade."""
        if self.old_name:
            self._apply_rename(self.old_name, self.new_name)
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `uv run pytest tests/commands/project/dataset/test_rename_column_command.py -v`
Expected: 6 PASS

- [ ] **Step 6: Run the full suite**

Run: `uv run pytest`
Expected: all PASS (395 existing + 6 new)

- [ ] **Step 7: Commit**

```bash
git add pandaplot/commands/project/dataset/rename_column_command.py pandaplot/models/events/event_data.py tests/commands/project/dataset/test_rename_column_command.py
git commit -m "feat: RenameColumnCommand renames column and cascades chart references"
```

---

### Task 2: UI wiring — context-menu action and table header refresh

**Files:**
- Modify: `pandaplot/gui/components/tabs/dataset/column_context_menu.py`
- Modify: `pandaplot/gui/components/tabs/dataset/pandas_table_model.py`

**Interfaces:**
- Consumes: `RenameColumnCommand(app_context, dataset_id, column_index, new_name)` and `DatasetColumnRenamedData` from Task 1; `DatasetOperationEvents.DATASET_COLUMN_RENAMED`.
- Produces: nothing consumed by later tasks.

- [ ] **Step 1: Add the "Rename column..." action to the header context menu**

In `pandaplot/gui/components/tabs/dataset/column_context_menu.py`:

Add imports:

```python
from PySide6.QtWidgets import QInputDialog, QMenu
from pandaplot.commands.project.dataset.rename_column_command import RenameColumnCommand
```

(`QMenu` is already imported — only add `QInputDialog` to that line.)

In `_init_ui`, inside the existing `if len(self.column_indices) == 1:` block, BEFORE the dtype submenu creation, add:

```python
            rename_action = QAction("Rename column...", self)
            rename_action.triggered.connect(self._rename_column)
            self.addAction(rename_action)
```

Add the handler method to the class:

```python
    def _rename_column(self):
        """Prompt for a new name for the selected column and execute the rename."""
        column_index = self.column_indices[0]
        project = self.app_context.app_state.current_project
        dataset = project.find_item(self.dataset_id) if project else None
        current_name = ""
        data = getattr(dataset, "data", None)
        if data is not None and 0 <= column_index < len(data.columns):
            current_name = str(data.columns[column_index])

        new_name, ok = QInputDialog.getText(
            self.parentWidget(), "Rename Column", "New column name:", text=current_name)
        if ok and new_name.strip():
            self.app_context.command_executor.execute_command(RenameColumnCommand(
                self.app_context, self.dataset_id, column_index, new_name))
```

- [ ] **Step 2: Refresh table headers on the rename event**

In `pandaplot/gui/components/tabs/dataset/pandas_table_model.py`:

Add `DatasetColumnRenamedData` to the existing `event_data` import line.

In `setup_event_subscriptions`, after the COLUMN_REMOVED subscription, add:

```python
        self.app_context.event_bus.subscribe(DatasetOperationEvents.DATASET_COLUMN_RENAMED, self.on_rename_column_event)
```

Add the handler next to `on_remove_column_event` (the existing handlers do not filter by dataset_id — follow that pattern; the header text is re-read from this model's own DataFrame, so a foreign event is a harmless repaint):

```python
    def on_rename_column_event(self, event):
        self.logger.info("On rename column event")
        event_data = DatasetColumnRenamedData.from_dict(event)
        self.headerDataChanged.emit(
            Qt.Orientation.Horizontal, event_data.column_index, event_data.column_index)
```

- [ ] **Step 3: Sanity checks and full suite**

Run: `uv run python -c "import pandaplot.gui.components.tabs.dataset.column_context_menu; import pandaplot.gui.components.tabs.dataset.pandas_table_model"`
Expected: clean import.
Run: `uv run pytest`
Expected: all PASS.

- [ ] **Step 4: Manual verification**

Run: `uv run python -m pandaplot.app`
1. Import a CSV, create a chart from it, note which columns the series uses.
2. In the dataset tab, right-click the used column's header → "Rename column..." → enter a new name. The header updates; the chart tab still renders (series now references the new name; check the properties panel's X/Y column display after clicking the chart tab).
3. Edit → Undo: header and chart revert. Edit → Redo: rename returns.
4. Try renaming a column to an existing column's name → error dialog, nothing changes.

- [ ] **Step 5: Commit**

```bash
git add pandaplot/gui/components/tabs/dataset/column_context_menu.py pandaplot/gui/components/tabs/dataset/pandas_table_model.py
git commit -m "feat: rename column from dataset header context menu"
```
