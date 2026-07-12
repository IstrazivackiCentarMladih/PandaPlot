# High #4 — Silent Failure in Item Loading

**Severity:** High  
**File:** `pandaplot/storage/project_data_manager.py`  
**Lines:** 56–67

---

## Problem

`_load_item()` wraps the entire load operation in a bare `except Exception` and returns `None` on any failure:

```python
# project_data_manager.py:56-67
def _load_item(self, item_id: str, info, zip_file) -> Item | None:
    try:
        item_class = self.data_factory.resolve_item_class(info["type"])
        path = info["path"]
        manager = self.data_factory.get_manager(info["type"])
        item = manager.load(item_class, zip_file, path)
        self.logger.info(
            f"Loaded item {item_id} of type {info['type']} from {path}")
        return item
    except Exception as ex:
        self.logger.error(f"Failed to load item {item_id}: {ex}")
        # returns None implicitly
```

The caller in `load()` checks `if curr_item is not None` but silently skips failed items:

```python
# project_data_manager.py:44-47
for item_id, info in items_info:
    curr_item = self._load_item(item_id, info, zf)
    if curr_item is not None:
        items[item_id] = curr_item
```

This means:
- A corrupt dataset, chart, or note in the `.pplot` file fails silently.
- The user is never informed — no dialog, no status bar message, nothing.
- The project opens in a partially-loaded state that looks complete but is missing data.
- The user may not discover the data loss until they try to use the missing item.

---

## Impact

- **Silent data loss**: users cannot distinguish between "project opened successfully" and "project opened with 3 items silently dropped".
- **Debugging difficulty**: the only evidence of failure is a log line at ERROR level, which most users never see.
- **Trust**: if users discover that saved work disappeared on reload, they lose confidence in the application's reliability.

---

## Fix

### 1. Collect failures and report them to the user

Rather than swallowing failures, collect them and surface a summary after the load completes:

```python
def load(self, filepath: str) -> Project:
    ...
    failed_items: list[str] = []

    for item_id, info in items_info:
        curr_item = self._load_item(item_id, info, zf)
        if curr_item is not None:
            items[item_id] = curr_item
        else:
            failed_items.append(item_id)

    ...

    if failed_items:
        # Caller (ProjectManager / command) should surface this to the user
        raise PartialLoadError(
            f"{len(failed_items)} item(s) could not be loaded: {failed_items}",
            loaded_project=project,
            failed_item_ids=failed_items
        )

    return project
```

Define `PartialLoadError` as a custom exception that carries both the (usable) project and the list of failures, so the caller can decide whether to proceed or abort:

```python
class PartialLoadError(Exception):
    def __init__(self, message: str, loaded_project: Project, failed_item_ids: list[str]):
        super().__init__(message)
        self.loaded_project = loaded_project
        self.failed_item_ids = failed_item_ids
```

### 2. Surface the error at the command layer

In `OpenProjectCommand` (or `ProjectManager.open_project()`), catch `PartialLoadError` and show a dialog:

```python
try:
    project = self.project_data_manager.load(filepath)
except PartialLoadError as e:
    self.ui_controller.show_warning(
        "Partial Load",
        f"The project was loaded, but {len(e.failed_item_ids)} item(s) could not be read "
        f"and have been skipped:\n\n" + "\n".join(e.failed_item_ids)
    )
    project = e.loaded_project  # continue with what was loaded
```

### 3. Preserve exception details in `_load_item` logging

Always log the full traceback, not just `str(ex)`, so developers can diagnose format issues:

```python
self.logger.error(f"Failed to load item {item_id}: {ex}", exc_info=True)
```

---

## Notes

- The `None` return type on `_load_item` is a code smell: returning sentinel values for errors makes failures invisible. Prefer raising or returning a typed result (`ItemLoadResult`) with an explicit error field.
- This fix is closely coupled to Critical #3 (zip file locked on Windows). Both issues stem from the same function and should be fixed in the same PR.
- Consider adding a test that intentionally corrupts one item entry in a zip archive and asserts that `PartialLoadError` is raised and `failed_item_ids` is populated correctly.
