# Rename Column — Design

**Goal:** Let the user rename a dataset column from the dataset table, keeping charts and fits that reference the column working, with a single undoable step.

## UI

- New action **"Rename column..."** in `ColumnHeaderContextMenu` (`pandaplot/gui/components/tabs/dataset/column_context_menu.py`), shown only when exactly one column is selected (same condition as the "Change Data Type" submenu).
- The action opens `QInputDialog.getText`, pre-filled with the current column name. OK executes `RenameColumnCommand` via `app_context.command_executor`; Cancel does nothing.

## Command

New file `pandaplot/commands/project/dataset/rename_column_command.py`, class `RenameColumnCommand(Command)`, constructor `(app_context, dataset_id: str, column_index: int, new_name: str)` — mirroring `ChangeColumnDtypeCommand`'s structure and validation style.

**execute():**
1. Validate: project loaded; dataset exists and is a `Dataset` with non-empty data; `column_index` in range. Error/warning dialogs via `ui_controller`, return `False` on failure.
2. Resolve `old_name = df.columns[column_index]`.
3. Validate `new_name`: stripped, non-empty and not already a column in this dataset (error dialog + return `False` on violation; nothing lands on the undo stack). A name identical to `old_name` is a silent no-op (return `False`, no dialog).
4. Rename: `dataset.data.rename(columns={old_name: new_name}, inplace=True)`.
5. Cascade: walk `project.get_all_items()` for `Chart` items. For each chart, for every `DataSeries` with `dataset_id == self.dataset_id`, replace `x_column`/`y_column` values equal to `old_name` with `new_name`; likewise `FitData.source_x_column`/`source_y_column` where `source_dataset_id` matches. Record the ids of affected charts. Series/fit **labels are not touched** (user-editable text).
6. Events: emit `DatasetOperationEvents.DATASET_COLUMN_RENAMED` (existing, currently unused constant) with a new `DatasetColumnRenamedData` payload (`dataset_id`, `column_index`, `old_name`, `new_name`) — the table model handles it by emitting `headerDataChanged` (a header change, not a cell-data change, so `DATASET_DATA_CHANGED` is the wrong event). Also emit `ChartEvents.CHART_UPDATED` with `{"chart_id", "chart"}` for each affected chart (the `"chart"` key makes the properties panel do a full resync, and open chart tabs re-render).

**undo()/redo():** run the same rename + cascade with old/new names swapped (undo) or as in execute (redo), emitting the same events. The command stores `old_name`/`new_name`; no data snapshot is needed because the rename walk is symmetric and lossless.

## Edge cases

- A series using the renamed column for both x and y: both fields updated.
- Columns with the same name in *other* datasets: untouched (matching requires the dataset id).
- Duplicate/empty/unchanged new name: rejected with a dialog before any mutation.
- After undo of a rename, previously affected charts render with the original name again (references were swapped back in the same step).

## Testing

Model-level pytest (no Qt widgets/QApplication), in `tests/commands/project/dataset/test_rename_column_command.py`, using a real `Project` + `Dataset` + `Chart` and a mock `app_context` (pattern: `tests/commands/project/note/test_create_note_command.py`):
- rename updates the DataFrame column,
- matching chart series and fit references updated; non-matching (other dataset id, other column) untouched,
- undo restores DataFrame and references; redo re-applies,
- duplicate, empty, and unchanged names are rejected (`execute()` returns `False`, DataFrame unchanged),
- CHART_UPDATED emitted only for charts that actually referenced the column.

## Why references stay name-based (and duplicate names stay rejected)

Charts and fits reference columns by name (`DataSeries.x_column`/`y_column`, `FitData.source_*`), and this feature keeps that, cascading renames instead of switching to positional or ID-based references. The alternatives were considered and rejected:

- **Index-based references** are fragile across structural edits: a chart saved pointing at column 2 silently plots the *wrong data* after a column is inserted or deleted. Name-based references fail loudly instead (the series is skipped and reported), which is the safer failure mode for persisted references. Indices are fine transiently — the context menu passes `column_index` at click time and the command resolves it to a name immediately — but must not be persisted.
- **(index, name) pairs** create two identities that can disagree after any edit; every consumer would need a resolution rule for "name matches at a different index". The pair relocates the ambiguity rather than removing it.
- **Duplicate column names fight pandas itself**: with two columns named `a`, `df["a"]` returns a two-column DataFrame instead of a Series (breaking the chart resolver, fits, transforms, and analysis), `df.rename(columns={"a": ...})` renames *both*, CSV round-trips mangle them to `a`/`a.1`, and column dropdowns would show indistinguishable entries. Hence the duplicate-name rejection in this command.

**Future alternative — stable column IDs:** if duplicate display names ever become a requirement, the right design is a persistent per-column UUID in dataset metadata; charts/fits reference IDs and the name becomes a display label. That removes the rename cascade entirely, but requires ID indirection through the whole stack (datasets, charts, fits, transforms, serialization, and a `.pplot` migration), so it is deliberately deferred.

## Out of scope

- Renaming when multiple columns are selected.
- Updating auto-generated series labels.
- Inline header editing (double-click) — can be layered on later, reusing the same command.
