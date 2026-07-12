# Dataset & Transform Bug Fixes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix three dataset-editing bugs: a dataset with zero columns has no way to add a column back, there is no way to rename a column, and the Transform tab silently only transforms the first of several selected columns and bypasses undo/redo entirely.

**Architecture:** `AddColumnsCommand` gets a dedicated "first column" path for empty datasets (its current validation hard-rejects any dataset with 0 rows or 0 columns, and its whole design assumes an existing column to insert relative to). A new `RenameColumnCommand` follows the existing `RenameItemCommand` pattern. The Transform panel is wired to pass every selected column through to `TransformColumnCommand` (which already has a working `multi_column` execution path — it's just never selected) and to execute via the command executor instead of calling `command.execute()` directly, restoring undo/redo.

**Tech Stack:** PySide6, pandas, pytest.

## Global Constraints

- The "Transform Type" dropdown (Math/String/Date-Time/Statistical) stays hint-only per your decision — no functional branching added for it. Add a one-line `# TODO` noting it's intentionally a placeholder-text hint, not a mode switch, for future work.
- Do not weaken `DeleteColumnsCommand`'s existing "cannot delete the last column" guard — it already prevents reaching zero columns through normal deletion; this plan only fixes *recovery* if a dataset is ever found with zero columns (e.g. from import or a future code path).
- Follow existing test convention: plain pytest functions, mirroring `tests/models/`'s style for command/model-level tests. Qt-only wiring (context menu items, dialogs) has no automated-test precedent in this repo — verify by code review + manual checklist.
- Run tests with `pytest` from the repo root.

---

### Task 1: Support adding the first column to an empty dataset

**Files:**
- Modify: `pandaplot/commands/project/dataset/add_columns_command.py`
- Modify: `pandaplot/gui/components/tabs/dataset/dataset_tab.py`
- Test: `tests/commands/project/dataset/test_add_columns_empty_dataset.py`

**Interfaces:**
- Produces: `AddColumnsCommand` now succeeds when called against a dataset with 0 columns (previously always rejected via the `.empty` check and the reference-position validation, both of which assume at least one existing column).
- Produces: a new "Add Column" button in the dataset tab's actions row, calling `AddColumnsCommand` with `reference_positions=[]`, which is now handled by the empty-dataset path regardless of whether the dataset currently has 0 or more columns (when it has existing columns, it appends after the last one).

- [ ] **Step 1: Write the failing tests**

Create `tests/commands/project/dataset/test_add_columns_empty_dataset.py`:

```python
"""
Unit tests for AddColumnsCommand's support for adding the first column(s)
to a dataset that currently has zero columns (previously impossible: the
command's own validation rejected any dataset with 0 rows or 0 columns,
and required existing columns to insert relative to).
"""

from unittest.mock import Mock

import pandas as pd
import pytest

from pandaplot.commands.project.dataset.add_columns_command import AddColumnsCommand
from pandaplot.gui.controllers.ui_controller import UIController
from pandaplot.models.project.items import Dataset
from pandaplot.models.state import AppContext, AppState


@pytest.fixture
def app_context_with_empty_dataset():
    """Mock AppContext wired to a real Dataset with 3 rows and 0 columns,
    following this repo's established command-test convention (Mock(spec=...)
    over a real Project/AppContext instance)."""
    dataset = Dataset(name="Empty Dataset")
    dataset.set_data(pd.DataFrame(index=range(3)))

    project = Mock()
    project.find_item = Mock(return_value=dataset)

    app_state = Mock(spec=AppState)
    app_state.has_project = True
    app_state.current_project = project
    app_state.event_bus = Mock()

    app_context = Mock(spec=AppContext)
    app_context.get_app_state.return_value = app_state
    app_context.get_ui_controller.return_value = Mock(spec=UIController)

    return app_context, dataset


def test_add_first_column_to_empty_dataset(app_context_with_empty_dataset):
    app_context, dataset = app_context_with_empty_dataset

    command = AddColumnsCommand(
        app_context, dataset.id,
        column_names=["Column1"],
        reference_positions=[],
        default_values=[0],
    )
    assert command.execute() is True
    assert list(dataset.data.columns) == ["Column1"]
    assert len(dataset.data) == 3
    assert (dataset.data["Column1"] == 0).all()


def test_add_multiple_first_columns_to_empty_dataset(app_context_with_empty_dataset):
    app_context, dataset = app_context_with_empty_dataset

    command = AddColumnsCommand(
        app_context, dataset.id,
        column_names=["A", "B"],
        reference_positions=[],
        default_values=[1, "x"],
    )
    assert command.execute() is True
    assert list(dataset.data.columns) == ["A", "B"]


def test_undo_restores_zero_columns(app_context_with_empty_dataset):
    app_context, dataset = app_context_with_empty_dataset

    command = AddColumnsCommand(
        app_context, dataset.id,
        column_names=["Column1"],
        reference_positions=[],
    )
    command.execute()
    command.undo()
    assert len(dataset.data.columns) == 0
    assert len(dataset.data) == 3  # rows preserved
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `pytest tests/commands/project/dataset/test_add_columns_empty_dataset.py -v`
Expected: FAIL — the "Cannot add columns to empty dataset" warning path returns `False`, so `command.execute() is True` assertions fail.

- [ ] **Step 3: Add the empty-dataset path**

In `pandaplot/commands/project/dataset/add_columns_command.py`, replace:

```python
            # Get current data
            if self.dataset.data is None or self.dataset.data.empty:
                self.ui_controller.show_warning_message(
                    "Add Columns", 
                    "Cannot add columns to empty dataset."
                )
                return False
            
            # Store original data for undo
            self.original_data = self.dataset.data.copy()
            
            # Validate reference positions
            num_cols = len(self.dataset.data.columns)
            for i, pos in enumerate(self.reference_positions):
                if pos < 0 or pos >= num_cols:
                    self.ui_controller.show_error_message(
                        "Add Columns", 
                        f"Reference position {pos} for column '{self.column_names[i]}' is out of bounds (0-{num_cols-1})."
                    )
                    return False
```

with:

```python
            # Get current data
            if self.dataset.data is None:
                self.ui_controller.show_warning_message(
                    "Add Columns", 
                    "Cannot add columns: dataset has no data loaded."
                )
                return False
            
            # Store original data for undo
            self.original_data = self.dataset.data.copy()
            
            num_cols = len(self.dataset.data.columns)
            
            if num_cols == 0:
                # No existing columns to insert relative to - just append the new
                # columns directly. This is the only way to recover a dataset that
                # has (or ends up with) zero columns.
                new_data = self._insert_column_block(
                    self.dataset.data, 0, self.column_names, self.default_values)
                self.dataset.set_data(new_data)
                self.final_insertion_positions = list(range(len(self.column_names)))
                
                self.app_state.event_bus.emit(DatasetOperationEvents.DATASET_COLUMN_ADDED, DatasetColumnsAddedData(
                    dataset_id=self.dataset_id,
                    column_positions=self.final_insertion_positions
                ).to_dict())
                
                self.logger.info(f"Added {len(self.column_names)} columns as the first columns of dataset '{self.dataset.name}' (ID: {self.dataset_id})")
                return True
            
            # Validate reference positions
            for i, pos in enumerate(self.reference_positions):
                if pos < 0 or pos >= num_cols:
                    self.ui_controller.show_error_message(
                        "Add Columns", 
                        f"Reference position {pos} for column '{self.column_names[i]}' is out of bounds (0-{num_cols-1})."
                    )
                    return False
```

Note: the duplicate-name checks below this block (`existing_columns = set(self.dataset.data.columns)`, etc.) are unreachable for the `num_cols == 0` case since it returns early — that's correct, there can be no existing columns to collide with.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `pytest tests/commands/project/dataset/test_add_columns_empty_dataset.py -v`
Expected: PASS (3 tests).

- [ ] **Step 5: Add an "Add Column" button so users can reach this without a header to right-click**

In `pandaplot/gui/components/tabs/dataset/dataset_tab.py`, add the import:

```python
from pandaplot.commands.project.dataset.add_columns_command import AddColumnsCommand
```

In `create_actions_section`, replace:

```python
        # Create chart button
        self.create_chart_btn = QPushButton("📈 Create Chart from Data")
        self.create_chart_btn.clicked.connect(self.create_chart_from_data)
        actions_layout.addWidget(self.create_chart_btn)
```

with:

```python
        # Add column button (only way to add a column when the dataset has none)
        self.add_column_btn = QPushButton("➕ Add Column")
        self.add_column_btn.clicked.connect(self.add_column)
        actions_layout.addWidget(self.add_column_btn)

        # Create chart button
        self.create_chart_btn = QPushButton("📈 Create Chart from Data")
        self.create_chart_btn.clicked.connect(self.create_chart_from_data)
        actions_layout.addWidget(self.create_chart_btn)
```

Add a handler method (near `create_chart_from_data`):

```python
    def add_column(self):
        """Add a new column, appended after any existing columns (or as the first
        column if the dataset currently has none)."""
        num_cols = len(self.dataset.data.columns) if self.dataset.data is not None else 0
        column_name = f"Column{num_cols + 1}"
        self.app_context.command_executor.execute_command(AddColumnsCommand(
            self.app_context,
            self.dataset.id,
            column_names=[column_name],
            reference_positions=[num_cols - 1] if num_cols > 0 else [],
            side="right",
        ))
```

- [ ] **Step 6: Run the full suite to check for regressions**

Run: `pytest`
Expected: PASS (374 passed — 371 pre-existing + 3 new).

- [ ] **Step 7: Manually verify in the running app**

Run: `python -m pandaplot`

1. Open a dataset, delete columns one at a time down to the last one — confirm the existing guard still blocks deleting the very last column (unchanged behavior).
2. On a dataset that still has one column, delete it via some other route if possible, or construct/import a dataset that ends up with zero columns. With zero columns, click "Add Column" in the actions row. Confirm a new column appears.
3. On a normal dataset with existing columns, click "Add Column". Confirm it appends a new column after the last one without disturbing existing data.

- [ ] **Step 8: Commit**

```bash
git add pandaplot/commands/project/dataset/add_columns_command.py pandaplot/gui/components/tabs/dataset/dataset_tab.py tests/commands/project/dataset/test_add_columns_empty_dataset.py
git commit -m "Support adding the first column(s) to an empty dataset"
```

---

### Task 2: Add column rename

**Files:**
- Create: `pandaplot/commands/project/dataset/rename_column_command.py`
- Modify: `pandaplot/gui/components/tabs/dataset/column_context_menu.py`
- Modify: `pandaplot/gui/components/tabs/dataset/dataset_tab.py`
- Test: `tests/commands/project/dataset/test_rename_column_command.py`

**Interfaces:**
- Produces: `RenameColumnCommand(app_context, dataset_id, column_index, new_name)`, modeled on `RenameItemCommand`, emitting the existing (currently unused) `DatasetOperationEvents.DATASET_COLUMN_RENAMED` event.
- Consumes: `Dataset` model (`pandaplot/models/project/items/dataset.py`) — renames via `dataset.data.rename(columns={...})` + `dataset.set_data(...)`.

- [ ] **Step 1: Write the failing tests**

Create `tests/commands/project/dataset/test_rename_column_command.py`:

```python
"""Unit tests for RenameColumnCommand."""

from unittest.mock import Mock

import pandas as pd
import pytest

from pandaplot.commands.project.dataset.rename_column_command import RenameColumnCommand
from pandaplot.gui.controllers.ui_controller import UIController
from pandaplot.models.project.items import Dataset
from pandaplot.models.state import AppContext, AppState


@pytest.fixture
def app_context_with_dataset():
    """Mock AppContext over a real Dataset, following this repo's established
    command-test convention (see tests/commands/project/note/test_create_note_command.py)."""
    dataset = Dataset(name="Test Dataset")
    dataset.set_data(pd.DataFrame({"x": [1, 2, 3], "y": [4, 5, 6]}))

    project = Mock()
    project.find_item = Mock(return_value=dataset)

    app_state = Mock(spec=AppState)
    app_state.has_project = True
    app_state.current_project = project
    app_state.event_bus = Mock()

    app_context = Mock(spec=AppContext)
    app_context.get_app_state.return_value = app_state
    app_context.get_ui_controller.return_value = Mock(spec=UIController)

    return app_context, dataset


def test_rename_column(app_context_with_dataset):
    app_context, dataset = app_context_with_dataset

    command = RenameColumnCommand(app_context, dataset.id, column_index=0, new_name="x_renamed")
    assert command.execute() is True
    assert list(dataset.data.columns) == ["x_renamed", "y"]


def test_rename_column_preserves_data(app_context_with_dataset):
    app_context, dataset = app_context_with_dataset

    command = RenameColumnCommand(app_context, dataset.id, column_index=1, new_name="y_renamed")
    command.execute()
    assert dataset.data["y_renamed"].tolist() == [4, 5, 6]


def test_rename_column_rejects_duplicate_name(app_context_with_dataset):
    app_context, dataset = app_context_with_dataset

    command = RenameColumnCommand(app_context, dataset.id, column_index=0, new_name="y")
    assert command.execute() is False
    assert list(dataset.data.columns) == ["x", "y"]  # unchanged


def test_undo_restores_original_name(app_context_with_dataset):
    app_context, dataset = app_context_with_dataset

    command = RenameColumnCommand(app_context, dataset.id, column_index=0, new_name="x_renamed")
    command.execute()
    command.undo()
    assert list(dataset.data.columns) == ["x", "y"]
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `pytest tests/commands/project/dataset/test_rename_column_command.py -v`
Expected: FAIL — `ImportError: cannot import name 'RenameColumnCommand'`.

- [ ] **Step 3: Implement `RenameColumnCommand`**

Create `pandaplot/commands/project/dataset/rename_column_command.py`:

```python
"""Command to rename a dataset column."""

from typing import Optional, override

from pandaplot.commands.base_command import Command
from pandaplot.gui.controllers.ui_controller import UIController
from pandaplot.models.events.event_types import DatasetOperationEvents
from pandaplot.models.project.items import Dataset
from pandaplot.models.state import AppContext, AppState


class RenameColumnCommand(Command):
    """Command to rename a single column in a dataset, by position."""

    def __init__(self, app_context: AppContext, dataset_id: str, column_index: int, new_name: str):
        super().__init__()
        self.app_context = app_context
        self.app_state: AppState = app_context.get_app_state()
        self.ui_controller: UIController = app_context.get_ui_controller()

        self.dataset_id = dataset_id
        self.column_index = column_index
        self.new_name = new_name

        # Store state for undo
        self.old_name: Optional[str] = None
        self.dataset: Optional[Dataset] = None

    @override
    def execute(self) -> bool:
        """Execute the rename column command."""
        try:
            if not self.app_state.has_project:
                self.ui_controller.show_warning_message(
                    "Rename Column", "No project is currently loaded.")
                return False

            project = self.app_state.current_project
            if not project:
                return False

            found_item = project.find_item(self.dataset_id)
            if not isinstance(found_item, Dataset) or found_item.data is None:
                self.ui_controller.show_error_message(
                    "Rename Column", f"Dataset with ID '{self.dataset_id}' not found.")
                return False
            self.dataset = found_item

            columns = list(self.dataset.data.columns)
            if self.column_index < 0 or self.column_index >= len(columns):
                self.ui_controller.show_error_message(
                    "Rename Column", f"Column index {self.column_index} is out of bounds.")
                return False

            self.old_name = columns[self.column_index]

            if self.new_name in columns and self.new_name != self.old_name:
                self.ui_controller.show_warning_message(
                    "Rename Column", f"A column named '{self.new_name}' already exists.")
                return False

            new_df = self.dataset.data.rename(columns={self.old_name: self.new_name})
            self.dataset.set_data(new_df)

            self.app_state.event_bus.emit(DatasetOperationEvents.DATASET_COLUMN_RENAMED, {
                "dataset_id": self.dataset_id,
                "column_index": self.column_index,
                "old_name": self.old_name,
                "new_name": self.new_name,
            })

            self.logger.info(
                "Renamed column '%s' -> '%s' in dataset '%s' (id=%s)",
                self.old_name, self.new_name, self.dataset.name, self.dataset_id
            )
            return True
        except Exception as e:
            error_msg = f"Failed to rename column: {e}"
            self.logger.error(error_msg, exc_info=True)
            self.ui_controller.show_error_message("Rename Column Error", error_msg)
            return False

    def undo(self):
        """Undo the rename column command."""
        try:
            if self.dataset is None or self.old_name is None:
                return
            new_df = self.dataset.data.rename(columns={self.new_name: self.old_name})
            self.dataset.set_data(new_df)

            self.app_state.event_bus.emit(DatasetOperationEvents.DATASET_COLUMN_RENAMED, {
                "dataset_id": self.dataset_id,
                "column_index": self.column_index,
                "old_name": self.new_name,
                "new_name": self.old_name,
            })
            self.logger.info(
                "Restored column name to '%s' (id=%s)", self.old_name, self.dataset_id)
        except Exception as e:
            error_msg = f"Failed to undo rename column: {e}"
            self.logger.error(error_msg, exc_info=True)
            self.ui_controller.show_error_message("Undo Error", error_msg)

    def redo(self):
        """Redo the rename column command."""
        return self.execute()
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `pytest tests/commands/project/dataset/test_rename_column_command.py -v`
Expected: PASS (4 tests).

- [ ] **Step 5: Add "Rename column" to the header context menu**

In `pandaplot/gui/components/tabs/dataset/column_context_menu.py`, add the import:

```python
from pandaplot.commands.project.dataset.rename_column_command import RenameColumnCommand
```

Add a "Rename column" action (only offered for a single-column selection, same guard already used for "Change Data Type"). Replace:

```python
        # Add dtype change submenu (only for single column selection)
        if len(self.column_indices) == 1:
            dtype_menu = QMenu("Change Data Type", self)
```

with:

```python
        # Rename column (only for single column selection)
        if len(self.column_indices) == 1:
            rename_action = QAction("Rename column", self)
            rename_action.triggered.connect(self._rename_column)
            self.addAction(rename_action)
            self.addSeparator()

        # Add dtype change submenu (only for single column selection)
        if len(self.column_indices) == 1:
            dtype_menu = QMenu("Change Data Type", self)
```

Add a handler method to `ColumnHeaderContextMenu`:

```python
    def _rename_column(self):
        column_index = self.column_indices[0]
        ui_controller = self.app_context.get_ui_controller()
        new_name = ui_controller.get_text_input("Rename Column", "New column name:")
        if new_name:
            self.app_context.command_executor.execute_command(RenameColumnCommand(
                self.app_context, self.dataset_id, column_index, new_name
            ))
```

- [ ] **Step 6: Refresh the table view on rename**

In `pandaplot/gui/components/tabs/dataset/dataset_tab.py`, add to `setup_event_subscriptions`:

```python
        self.subscribe_to_event(
            DatasetOperationEvents.DATASET_COLUMN_RENAMED, self.on_dataset_column_renamed)
```

Add a handler:

```python
    def on_dataset_column_renamed(self, event_data):
        """Handle when a column is renamed in any dataset."""
        dataset_id = event_data.get("dataset_id")
        if dataset_id == self.dataset.id:
            self.logger.info("Column renamed event received for dataset %s", dataset_id)
            self.load_dataset_data()  # Refresh the table to show the new header
```

- [ ] **Step 7: Run the full suite to check for regressions**

Run: `pytest`
Expected: PASS (378 passed — 374 pre-existing + 4 new).

- [ ] **Step 8: Manually verify in the running app**

Run: `python -m pandaplot`

1. Right-click a single column header. Confirm "Rename column" appears.
2. Rename it. Confirm the header updates and existing data in that column is unchanged.
3. Try renaming a column to a name that already exists on another column. Confirm it's rejected with a message and nothing changes.
4. Select multiple columns and right-click. Confirm "Rename column" does NOT appear (single-selection only, same as "Change Data Type").
5. Undo (Ctrl+Z). Confirm the column name reverts.

- [ ] **Step 9: Commit**

```bash
git add pandaplot/commands/project/dataset/rename_column_command.py pandaplot/gui/components/tabs/dataset/column_context_menu.py pandaplot/gui/components/tabs/dataset/dataset_tab.py tests/commands/project/dataset/test_rename_column_command.py
git commit -m "Add column rename via the header context menu"
```

---

### Task 3: Fix Transform tab's multi-column selection and undo/redo

**Files:**
- Modify: `pandaplot/gui/components/sidebar/transform/transform_controller.py`
- Modify: `pandaplot/gui/components/sidebar/transform/transform_panel.py`
- Test: `tests/gui/test_transform_controller_multi_column.py`

**Interfaces:**
- Changes: `TransformController.apply_transformation()`'s `source_column: str` parameter becomes `source_columns: List[str]`; `transform_type` is now derived from the number of columns (`"multi_column"` for 2+, `"column"` for 1) instead of always `"column"`.
- Changes: `apply_transformation()` now executes via `self.app_context.command_executor.execute_command(command)` instead of calling `command.execute()` directly, so transforms land on the undo stack like every other dataset edit.

No automated test for the undo/redo wiring itself (it's a one-line call-site change verified by reading the code — `CommandExecutor.execute_command` is already covered by its own tests elsewhere). The multi-column fix is tested directly against `TransformController`.

- [ ] **Step 1: Write the failing test for multi-column selection**

Create `tests/gui/test_transform_controller_multi_column.py`:

```python
"""
Unit tests for TransformController.apply_transformation() correctly using
ALL selected source columns (previously only ever used the first one), and
executing through the command executor so transforms are undoable.
"""

from unittest.mock import Mock

import pandas as pd
import pytest

from pandaplot.commands.command_executor import CommandExecutor
from pandaplot.gui.components.sidebar.transform.transform_controller import TransformController
from pandaplot.models.project.items import Dataset
from pandaplot.models.state import AppContext


@pytest.fixture
def app_context_with_dataset():
    """Mock AppContext over a real Dataset. Note: TransformController and
    TransformColumnCommand both read `app_context.app_state` as a direct
    attribute (not the get_app_state() method used elsewhere in this repo),
    and use a real CommandExecutor so the undo-stack assertions are genuine."""
    dataset = Dataset(name="Test Dataset")
    dataset.set_data(pd.DataFrame({"a": [1, 2, 3], "b": [10, 20, 30]}))

    project = Mock()
    project.find_item = Mock(return_value=dataset)

    app_state = Mock()
    app_state.current_project = project

    app_context = Mock(spec=AppContext)
    app_context.app_state = app_state
    app_context.command_executor = CommandExecutor()

    return app_context, dataset


def test_single_column_uses_column_transform_type(app_context_with_dataset):
    app_context, dataset = app_context_with_dataset
    controller = TransformController(app_context)

    success = controller.apply_transformation(
        dataset_id=dataset.id,
        source_columns=["a"],
        new_column_name="a_doubled",
        function_code="value * 2",
    )
    assert success is True
    assert dataset.data["a_doubled"].tolist() == [2, 4, 6]


def test_multi_column_uses_all_selected_columns(app_context_with_dataset):
    app_context, dataset = app_context_with_dataset
    controller = TransformController(app_context)

    success = controller.apply_transformation(
        dataset_id=dataset.id,
        source_columns=["a", "b"],
        new_column_name="sum_ab",
        function_code="cols['a'] + cols['b']",
    )
    assert success is True
    assert dataset.data["sum_ab"].tolist() == [11, 22, 33]


def test_transform_is_undoable(app_context_with_dataset):
    app_context, dataset = app_context_with_dataset
    controller = TransformController(app_context)

    controller.apply_transformation(
        dataset_id=dataset.id,
        source_columns=["a"],
        new_column_name="a_doubled",
        function_code="value * 2",
    )
    assert len(app_context.command_executor.undo_stack) == 1
    app_context.command_executor.undo()
    assert "a_doubled" not in dataset.data.columns
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `pytest tests/gui/test_transform_controller_multi_column.py -v`
Expected: FAIL — `TypeError: apply_transformation() got an unexpected keyword argument 'source_columns'`.

- [ ] **Step 3: Update `apply_transformation` to accept and use all source columns, and execute through the command executor**

In `pandaplot/gui/components/sidebar/transform/transform_controller.py`, replace:

```python
    def apply_transformation(self, dataset_id: str, source_column: str, 
                           new_column_name: str, function_code: str, 
                           replace_existing: bool = False) -> bool:
```

with:

```python
    def apply_transformation(self, dataset_id: str, source_columns: List[str], 
                           new_column_name: str, function_code: str, 
                           replace_existing: bool = False) -> bool:
```

(add `from typing import List` to the imports if not already present).

Replace the body's column-existence check:

```python
            df = dataset.data
            if source_column not in df.columns:
                self.transform_failed.emit(dataset_id, f"Column '{source_column}' not found")
                return False
```

with:

```python
            df = dataset.data
            missing = [c for c in source_columns if c not in df.columns]
            if missing:
                self.transform_failed.emit(dataset_id, f"Column(s) not found: {', '.join(missing)}")
                return False
```

Replace the transform-config construction and execution:

```python
            # Create transform configuration
            transform_config = {
                "new_column_name": new_column_name,
                "transform_type": "column",  # Default to column operation for now
                "source_columns": [source_column],
                "expression": function_code,
                "replace_existing": replace_existing
            }
            
            # Create and execute command
            command = TransformColumnCommand(self.app_context, dataset_id, transform_config)
            
            # TODO: Execute through app context command executor when available
            # For now, execute directly
            if command.execute():
```

with:

```python
            # Create transform configuration.
            # NOTE: "transform_type" here means arity (column/multi_column), not the
            # panel's "Transform Type" category (Math/String/etc, which is currently
            # a placeholder-text hint only - see transform_panel.py TODO).
            transform_config = {
                "new_column_name": new_column_name,
                "transform_type": "multi_column" if len(source_columns) > 1 else "column",
                "source_columns": source_columns,
                "expression": function_code,
                "replace_existing": replace_existing
            }
            
            # Create and execute command through the command executor so it lands
            # on the undo stack like every other dataset edit.
            command = TransformColumnCommand(self.app_context, dataset_id, transform_config)
            
            if self.app_context.command_executor.execute_command(command):
```

- [ ] **Step 4: Preview must also use all selected columns**

`preview_transform` (the method building `preview_result`, used by the panel's "Preview" button) has the same single-column call-site issue. In `transform_panel.py`, find where `preview_transform` is invoked (the call passing `source_column=source_column`) and update the panel side in Step 5 below — the controller's `preview_transform` itself only needs to keep working for a single representative column (previews are illustrative, not the actual multi-column application), so no controller-side change is needed here beyond what Step 3 already did for `apply_transformation`.

- [ ] **Step 5: Update the panel to pass all selected columns to `apply_transform`**

In `pandaplot/gui/components/sidebar/transform/transform_panel.py`, replace:

```python
    def apply_transform(self):
        """Apply the transformation to the dataset."""
        selected_columns = self.get_selected_columns()
        if not self.current_dataset or not selected_columns:
            self.logger.warning("TransformPanel: no dataset or source column selected for transform")
            return
        
        source_column = selected_columns[0]  # Use first selected column for transformation
        new_column_name = self.new_column_name.text().strip()
```

with:

```python
    def apply_transform(self):
        """Apply the transformation to the dataset."""
        selected_columns = self.get_selected_columns()
        if not self.current_dataset or not selected_columns:
            self.logger.warning("TransformPanel: no dataset or source column selected for transform")
            return
        
        new_column_name = self.new_column_name.text().strip()
```

Replace:

```python
            # Apply transformation through controller
            success = self.transform_controller.apply_transformation(
                dataset_id=dataset_id,
                source_column=source_column,
                new_column_name=new_column_name,
                function_code=function_code,
                replace_existing=replace_existing
            )
            
            if success:
                # Publish transform completion event
                self.publish_event(DatasetOperationEvents.DATASET_COLUMN_ADDED, {
                    "dataset_id": dataset_id,
                    "column_name": new_column_name,
                    "transform_type": "custom_function",
                    "source_column": source_column,
                    "function_code": function_code
                })
                self.logger.info("TransformPanel: transform applied %s -> %s using %s", source_column, new_column_name, function_code)
```

with:

```python
            # Apply transformation through controller
            success = self.transform_controller.apply_transformation(
                dataset_id=dataset_id,
                source_columns=selected_columns,
                new_column_name=new_column_name,
                function_code=function_code,
                replace_existing=replace_existing
            )
            
            if success:
                # Publish transform completion event
                self.publish_event(DatasetOperationEvents.DATASET_COLUMN_ADDED, {
                    "dataset_id": dataset_id,
                    "column_name": new_column_name,
                    "transform_type": "custom_function",
                    "source_columns": selected_columns,
                    "function_code": function_code
                })
                self.logger.info("TransformPanel: transform applied %s -> %s using %s", selected_columns, new_column_name, function_code)
```

- [ ] **Step 6: Mark the Transform Type dropdown as intentionally hint-only**

In `on_transform_type_changed`, add a one-line comment above the `placeholders` dict:

```python
        # TODO: this selector only changes the placeholder hint text below; it does
        # not restrict or validate the expression against the chosen category. Left
        # as a future enhancement - see docs/superpowers/plans/2026-07-12-dataset-transform-bugfixes.md.
        placeholders = {
```

- [ ] **Step 7: Run the tests to verify they pass**

Run: `pytest tests/gui/test_transform_controller_multi_column.py -v`
Expected: PASS (3 tests).

- [ ] **Step 8: Run the full suite to check for regressions**

Run: `pytest`
Expected: PASS (381 passed — 378 pre-existing + 3 new).

- [ ] **Step 9: Manually verify in the running app**

Run: `python -m pandaplot`

1. Open the Transform tab on a dataset with 2+ numeric columns. Select two columns, enter an expression using `cols['<name>']` for each, e.g. `cols['a'] + cols['b']`. Apply. Confirm the new column reflects both source columns, not just the first.
2. Press Ctrl+Z. Confirm the transform is undone (new column disappears) — previously impossible.
3. Redo (Ctrl+Y / Ctrl+Shift+Z). Confirm the column reappears.
4. Apply a single-column transform (e.g. `value * 2`) as before. Confirm it still works exactly as before (arity-1 path unchanged).

- [ ] **Step 10: Commit**

```bash
git add pandaplot/gui/components/sidebar/transform/transform_controller.py pandaplot/gui/components/sidebar/transform/transform_panel.py tests/gui/test_transform_controller_multi_column.py
git commit -m "Fix Transform tab: use all selected columns and restore undo/redo"
```
