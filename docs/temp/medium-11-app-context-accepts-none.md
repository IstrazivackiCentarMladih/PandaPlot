# Medium #11 — AppContext Accepts None Managers Without Validation

**Severity:** Medium  
**File:** `pandaplot/models/state/app_context.py`  
**Lines:** 25–27

---

## Problem

`AppContext.__init__` stores managers by their type without validating that each manager is non-None:

```python
# app_context.py:25-27
self._managers: dict[type, Any] = {}
for manager in managers:
    self._managers[type(manager)] = manager
```

If a `None` value is passed in the `managers` list:
- `type(None)` is `<class 'NoneType'>`.
- The entry `{NoneType: None}` is stored.
- The actual manager type (e.g., `CommandExecutor`) is never registered.

`get_manager()` does check for `None` after retrieval:

```python
# app_context.py:48-53
manager = self._managers[manager_type]
if manager is None:
    raise RuntimeError(f"{manager_type.__name__} not initialized in AppContext")
```

But this check can only fire if the correct type is registered — which it isn't when `None` was passed. Instead, calling `get_manager(CommandExecutor)` would raise a `KeyError` (`"Manager of type CommandExecutor not found in AppContext"`), not the more descriptive `RuntimeError`.

Backward-compatibility shortcuts in `__init__` also fail at construction time if any manager is missing:

```python
# app_context.py:30-32
self.command_executor = self.get_manager(CommandExecutor)
self.ui_controller = self.get_manager(UIController)
self.task_scheduler = self.get_manager(TaskScheduler)
```

A `None` slipping in would cause a `KeyError` at `AppContext.__init__`, crashing startup with an unhelpful error message that points at the context rather than the misconfigured manager.

The risk is real: `app.py` constructs the managers list manually. Any refactor that adds a conditional manager (e.g., "only create `TaskScheduler` if threading is enabled") could accidentally pass `None`.

---

## Impact

- A misconfigured startup produces a `KeyError` at the wrong level, making it hard to identify which manager was missing.
- `type(None)` occupying a slot in `_managers` could shadow future registrations if the code is changed to allow re-registration.
- No fail-fast validation means configuration errors are discovered late (at first `get_manager()` call) rather than at startup.

---

## Fix

### 1. Validate at registration time

```python
self._managers: dict[type, Any] = {}
for manager in managers:
    if manager is None:
        raise ValueError(
            "AppContext received a None manager. All managers must be initialized before "
            "passing them to AppContext."
        )
    manager_type = type(manager)
    if manager_type in self._managers:
        raise ValueError(
            f"Duplicate manager type registered in AppContext: {manager_type.__name__}. "
            f"Each manager type may only be registered once."
        )
    self._managers[manager_type] = manager
```

This surfaces configuration errors at the earliest possible moment (application startup) with a clear message.

### 2. Remove the redundant None check in `get_manager()`

Once None is rejected at registration, the `if manager is None` guard in `get_manager()` becomes unreachable and can be removed:

```python
def get_manager(self, manager_type: type[T]) -> T:
    if manager_type not in self._managers:
        raise KeyError(f"Manager of type {manager_type.__name__} not found in AppContext")
    return self._managers[manager_type]
```

### 3. Type the `managers` parameter more strictly

```python
def __init__(
    self,
    app_state: AppState,
    event_bus: EventBus,
    managers: list[object]   # or a Protocol-typed list
):
```

Or define a `Manager` Protocol/base class that all managers implement, providing type safety at the call site in `app.py`.

---

## Notes

- The duplicate-registration check (step 1) is optional but catches a related class of bugs: accidentally registering a subclass and a base class separately, which could confuse `get_manager()` lookups.
- This is a defensive programming improvement. The actual probability of `None` being passed today is low, but it costs nothing to validate and provides clear error messages during future development.
