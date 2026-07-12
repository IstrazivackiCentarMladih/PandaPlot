# Medium #10 — Project Root Not Deserialized in `from_dict()`

**Severity:** Medium  
**File:** `pandaplot/models/project/project.py`  
**Lines:** 126–138

---

## Problem

`Project.from_dict()` creates a new `Project` (which initializes a fresh `ItemCollection` as root), restores basic metadata, but leaves a TODO for the root hierarchy:

```python
# project.py:126-138
@classmethod
def from_dict(cls, data: Dict[str, Any]) -> 'Project':
    """Create project from dictionary."""
    project = cls(
        name=data.get('name', 'Untitled Project'),
        description=data.get('description', '')
    )
    project.metadata = data.get('metadata', {})
    project.version = data.get('version', '1.0')
    project.project_file_path = data.get('path', None)

    # TODO: Parse root hierarchy when item types are fully implemented
    return project
```

`Project.to_dict()` serializes the root's ID:

```python
# project.py:115-124
def to_dict(self) -> Dict[str, Any]:
    return {
        'name': self.name,
        'description': self.description,
        'root': self.root.to_dict(),   # ← serializes root including its ID
        ...
    }
```

`ProjectDataManager.load()` partially compensates by restoring the root's `id` after calling `from_dict()`:

```python
# project_data_manager.py:49-50
project_root = project_dict.get("root", {})
project.root.id = project_root.get("id", project.root.id)
```

However, any **other state on the root `ItemCollection`** that is serialized by `to_dict()` (e.g., the root's `name`, `description`, custom metadata, or ordering) is not restored. The root is always a freshly constructed `ItemCollection` with default values.

Additionally, `_add_items_to_project()` in `project_data_manager.py` uses `node.get("parent_id")` to determine where each item goes. Items that belong directly to root will have `parent_id == root.id`. This lookup uses `Project.find_item(parent_id)`:

```python
# project.py:88-92
def find_item(self, item_id: str) -> Optional[Item]:
    if item_id == self.root.id:
        return self.root
    return self.items_index.get(item_id)
```

Because `project.root.id` is patched after `from_dict()`, this currently works — but only because `ProjectDataManager` does the patching outside of `from_dict()`. This is a leaky abstraction: the data manager should not need to know about `Project` internals to restore it correctly.

---

## Impact

- If the root `ItemCollection` has any serializable state beyond its `id` (e.g., a custom name, metadata, ordering), that state is silently dropped on every load.
- The responsibility split between `from_dict()` (incomplete) and `ProjectDataManager` (partial compensation) is fragile: adding new fields to root requires updating both places.
- Any test that round-trips a project through `to_dict()` → `from_dict()` will produce a different root than the original, making it hard to write reliable serialization tests.

---

## Fix

### Option A — Complete `from_dict()` to restore root state

`Project.from_dict()` should restore everything that `to_dict()` serializes about the root:

```python
@classmethod
def from_dict(cls, data: Dict[str, Any]) -> 'Project':
    project = cls(
        name=data.get('name', 'Untitled Project'),
        description=data.get('description', '')
    )
    project.metadata = data.get('metadata', {})
    project.version = data.get('version', '1.0')
    project.project_file_path = data.get('path', None)

    root_data = data.get('root', {})
    if root_data:
        project.root.id = root_data.get('id', project.root.id)
        project.root.name = root_data.get('name', project.root.name)
        # Restore any other root fields serialized by ItemCollection.to_dict()

    return project
```

Then remove the patch in `ProjectDataManager.load()`:

```python
# Remove these lines from project_data_manager.py:49-50:
# project_root = project_dict.get("root", {})
# project.root.id = project_root.get("id", project.root.id)
```

### Option B — Delegate root deserialization to `ItemCollection.from_dict()`

If `ItemCollection` already has a `from_dict()` class method (or should have one), use it:

```python
root_data = data.get('root', {})
if root_data:
    project.root = ItemCollection.from_dict(root_data)
```

This keeps the deserialization logic inside the model class where it belongs.

---

## Notes

- The TODO comment on line 137 (`# TODO: Parse root hierarchy when item types are fully implemented`) suggests this was intentionally deferred. This ticket is the plan to address that deferral.
- The item children of root are restored separately in `_add_items_to_project()` — that part works correctly. Only the root's own properties need to be restored here.
- Fixing this will allow reliable round-trip serialization tests: `project == Project.from_dict(project.to_dict())`.
