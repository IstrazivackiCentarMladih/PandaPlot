# Medium #12 — Orphaned Items Silently Reparented to Root

**Severity:** Medium  
**File:** `pandaplot/storage/project_data_manager.py`  
**Lines:** 69–80  
**Related file:** `pandaplot/models/project/project.py` lines 30–44

---

## Problem

`_add_items_to_project()` recursively walks the saved project tree and adds each item to the project using its `parent_id`:

```python
# project_data_manager.py:69-80
def _add_items_to_project(self, project: Project, items: dict[str, Item], project_tree: list[dict]) -> None:
    for node in project_tree:
        item_id = node.get("id")
        if item_id in items:
            project.add_item(
                items[item_id], parent_id=node.get("parent_id"))

        if node.get("items", None) is not None:
            self._add_items_to_project(
                project, items, node.get("items", []))
```

`Project.add_item()` handles a missing parent by falling back to root:

```python
# project.py:30-44
def add_item(self, item: Item, parent_id: Optional[str] = None):
    if parent_id is None:
        self.root.add_item(item)
    else:
        parent = self.find_item(parent_id)
        if parent is not None and isinstance(parent, ItemCollection):
            parent.add_item(item)
        else:
            self.logger.warning(
                f"Parent {parent_id} not found or not a collection, item: {item.id} {item.name} ")
            # Falls back to root silently
            self.root.add_item(item)
```

When an item's saved `parent_id` does not match any loaded item — due to a corrupt file, a partially-loaded project (see High #4), or a serialization bug — the item is silently attached to root. The warning is only logged; no exception is raised, no user notification is shown.

**Scenario:** A user creates a folder hierarchy (`Project Root → Experiments → Trial 1`). If `Experiments` fails to load (High #4), `Trial 1` is silently moved to root. The user sees `Trial 1` at the top level with no indication that the structure changed.

Additionally, `_add_items_to_project()` checks `if item_id in items` (line 72) but does NOT check whether the node's `parent_id` will be resolvable. It processes children even when the parent item was not successfully loaded, meaning orphaned children are added before the parent reference is established.

---

## Impact

- The restored project tree structure silently differs from what was saved.
- Users cannot tell that items were moved.
- Saving the "repaired" project would permanently overwrite the correct structure with the wrong one.
- This compounds with High #4 (items that fail to load become missing parents, causing their children to be orphaned).

---

## Fix

### 1. Log orphaned items with their full lineage

At minimum, make the warning more actionable by including the item type and expected parent:

```python
# project.py:add_item()
self.logger.warning(
    "Item '%s' (id=%s, type=%s) could not be added to parent '%s' — "
    "parent not found or not a collection. Falling back to root.",
    item.name, item.id, type(item).__name__, parent_id
)
```

### 2. Validate the tree before adding items

Before starting `_add_items_to_project()`, scan the tree to identify items whose `parent_id` is missing from the `items` dict:

```python
def _validate_tree(self, items: dict[str, Item], project_tree: list[dict], root_id: str) -> list[str]:
    """Returns list of item_ids that will be orphaned."""
    orphaned = []
    self._validate_nodes(items, project_tree, root_id, orphaned)
    return orphaned

def _validate_nodes(self, items, nodes, root_id, orphaned):
    for node in nodes:
        item_id = node.get("id")
        parent_id = node.get("parent_id")
        if item_id in items and parent_id and parent_id != root_id:
            if parent_id not in items:
                orphaned.append(item_id)
        if node.get("items"):
            self._validate_nodes(items, node["items"], root_id, orphaned)
```

Then surface the validation result to the caller (raise `PartialLoadError` from High #4, or include it in the existing partial-load error).

### 3. Abort rather than silently reparent (optional, stricter)

For a stricter approach, raise an exception instead of falling back to root:

```python
# project.py:add_item()
else:
    raise ValueError(
        f"Cannot add item '{item.name}' (id={item.id}): "
        f"parent '{parent_id}' not found or not a collection."
    )
```

This requires the caller to explicitly handle orphan cases, preventing silent structural corruption.

---

## Notes

- The silent fallback to root was probably added as a defensive measure to prevent a crash during load. It's a reasonable short-term choice, but the lack of user notification makes it dangerous in practice.
- This issue is closely coupled with High #4 (silent item load failure). An item that fails to load becomes a missing parent for its children, triggering this silent reparenting. Fixing High #4 reduces the frequency of this scenario.
- Consider adding a "project health check" function that can detect orphaned items, duplicate IDs, or broken parent-child relationships in a loaded project.
