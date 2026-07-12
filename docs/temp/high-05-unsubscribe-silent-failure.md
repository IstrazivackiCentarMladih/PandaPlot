# High #5 — Unsubscribe Can Fail Silently in EventBus

**Severity:** High  
**File:** `pandaplot/models/events/event_bus.py`  
**Lines:** 37–58

---

## Problem

`subscribe()` and `unsubscribe()` each independently convert a glob pattern to a regex string and use that string as a dictionary key:

```python
# event_bus.py:28-35 (subscribe)
if '*' in event_pattern:
    regex_pattern = event_pattern.replace('.', r'\.').replace('*', '.*')
    self._pattern_subscribers[regex_pattern].append(callback)

# event_bus.py:46-52 (unsubscribe)
if '*' in event_pattern:
    regex_pattern = event_pattern.replace('.', r'\.').replace('*', '.*')
    if callback in self._pattern_subscribers[regex_pattern]:
        self._pattern_subscribers[regex_pattern].remove(callback)
    else:
        self.logger.warning("Callback not found in pattern subscribers for: %s", event_pattern)
```

The pattern conversion is deterministic for the same input string, so the basic case works. However, the design has two structural weaknesses:

### Weakness A — Conversion logic duplicated in two places

The regex conversion is copy-pasted between `subscribe()` and `unsubscribe()`. Any future change to how patterns are converted (e.g., supporting `?` wildcards, anchoring with `^`/`$`, handling escaped dots) must be applied in both places. If one is updated and the other is not, `subscribe` and `unsubscribe` will generate different regex strings for the same input pattern, causing the lookup to fail silently.

### Weakness B — `unsubscribe` failure is only a warning

When the callback is not found, the method logs a warning and returns silently:

```python
else:
    self.logger.warning("Callback not found in pattern subscribers for: %s", event_pattern)
```

The caller has no way to know that unsubscription failed. The callback stays registered and continues to fire on every matching event. Over time this accumulates stale callbacks, especially in UI components that are repeatedly created and destroyed (e.g., panels that subscribe on `__init__` and unsubscribe on `closeEvent`).

The same silent-failure behaviour applies to direct (non-pattern) subscribers:

```python
# event_bus.py:54-58
if callback in self._subscribers[event_pattern]:
    self._subscribers[event_pattern].remove(callback)
else:
    self.logger.warning("Callback not found in direct subscribers for: %s", event_pattern)
```

---

## Impact

- Stale callbacks accumulate across the session lifetime.
- UI objects that are "destroyed" still receive events, causing `RuntimeError` (accessing deleted Qt widgets) or subtle state corruption.
- Very hard to debug because there is no visible error — the warning goes to the log, not the user.

---

## Fix

### 1. Extract the pattern conversion into a single private method

```python
@staticmethod
def _pattern_to_regex(event_pattern: str) -> str:
    return event_pattern.replace('.', r'\.').replace('*', '.*')
```

Use it in both `subscribe` and `unsubscribe`. Now there is one source of truth.

### 2. Cache the compiled regex alongside its string key

Store a tuple `(regex_string, compiled_regex)` so `emit()` doesn't recompile on every call:

```python
# Store as: {regex_string: (compiled_pattern, [callbacks])}
self._pattern_subscribers: dict[str, tuple[re.Pattern, list]] = {}
```

### 3. Raise (or at minimum return `bool`) from `unsubscribe` on failure

Components that subscribe should be able to detect and handle a failed unsubscription:

```python
def unsubscribe(self, event_pattern: str, callback: Callable) -> bool:
    """Returns True if callback was removed, False if it was not found."""
    if '*' in event_pattern:
        regex_pattern = self._pattern_to_regex(event_pattern)
        callbacks = self._pattern_subscribers.get(regex_pattern, (None, []))[1]
    else:
        callbacks = self._subscribers.get(event_pattern, [])

    if callback in callbacks:
        callbacks.remove(callback)
        return True

    self.logger.warning("unsubscribe: callback not found for pattern '%s'", event_pattern)
    return False
```

Callers that care about correctness (e.g., widget teardown) can then assert:

```python
assert self.event_bus.unsubscribe("dataset.*", self._on_dataset_changed), \
    "EventBus: failed to unsubscribe _on_dataset_changed"
```

---

## Notes

- The current conversion `event_pattern.replace('.', r'\.').replace('*', '.*')` does not anchor the regex. The pattern `dataset.*` will match `dataset.changed` but also `my_dataset.changed`. Consider anchoring: `'^' + pattern + '$'`.
- A subscription token pattern (where `subscribe` returns an opaque ID that `unsubscribe` accepts) would eliminate the duplicate-conversion problem entirely, at the cost of a slightly different API.
- Related: Medium #9 covers the performance impact of uncompiled regex patterns on every `emit()`.
