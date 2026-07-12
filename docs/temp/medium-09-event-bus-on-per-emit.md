# Medium #9 — EventBus Pattern Matching Is O(n) Per Emit

**Severity:** Medium  
**File:** `pandaplot/models/events/event_bus.py`  
**Lines:** 94–109

---

## Problem

Every call to `emit()` iterates over **all pattern subscribers** and tests each regex against the current event type:

```python
# event_bus.py:94-109
for pattern, callbacks in self._pattern_subscribers.items():
    if re.match(pattern, event_level):
        pattern_matches += len(callbacks)
        for callback in callbacks:
            try:
                callback(event_data)
            except Exception as e:
                ...
```

This loop runs once per hierarchy level per emit. With the event hierarchy (`EventHierarchy.get_hierarchy()`), a single `emit()` can fire multiple `event_level` values. For each level, every pattern is tested with `re.match()`.

**Two compounding issues:**

1. **No regex compilation cache**: The pattern strings stored in `_pattern_subscribers` are raw strings. `re.match(pattern, ...)` compiles the regex internally on each call. While Python's `re` module has a small internal LRU cache (128 entries by default), this cache is shared across the entire application and can be evicted by other `re` usage.

2. **Linear scan across all patterns**: With `n` pattern subscribers, every emit is O(n). In a typical session with many active panel subscriptions (e.g., analysis panel subscribes to `dataset.*`, chart panel subscribes to `chart.*`, etc.), `n` grows proportionally to the number of open panels — and `emit()` is called on every cell edit, every chart update, every dataset change.

---

## Impact

- High-frequency events (e.g., rapid cell edits in a large dataset, drag operations on chart series) trigger many `emit()` calls per second.
- Each emit does O(n) regex matching, causing CPU spikes and UI jank.
- The problem compounds with the event hierarchy: a single specific event like `DATASET_COLUMN_DATA_CHANGED` may emit 3–4 hierarchy levels, multiplying the work by 3–4x.

---

## Fix

### 1. Pre-compile regex patterns at subscribe time

Store compiled `re.Pattern` objects instead of raw strings:

```python
from __future__ import annotations
import re
from collections import defaultdict
from typing import Callable, Dict, Any

class EventBus:
    def __init__(self):
        self._subscribers: dict[str, list[Callable]] = defaultdict(list)
        # key: raw pattern string, value: (compiled regex, callbacks)
        self._pattern_subscribers: dict[str, tuple[re.Pattern, list[Callable]]] = {}

    def subscribe(self, event_pattern: str, callback: Callable) -> None:
        if '*' in event_pattern:
            regex_str = '^' + event_pattern.replace('.', r'\.').replace('*', '.*') + '$'
            if regex_str not in self._pattern_subscribers:
                self._pattern_subscribers[regex_str] = (re.compile(regex_str), [])
            self._pattern_subscribers[regex_str][1].append(callback)
        else:
            self._subscribers[event_pattern].append(callback)
```

In `emit()`, use the pre-compiled pattern:

```python
for regex_str, (compiled, callbacks) in self._pattern_subscribers.items():
    if compiled.match(event_level):
        for callback in callbacks:
            ...
```

This eliminates repeated compilation. The compiled `re.Pattern` object is reused on every emit.

### 2. Add regex anchoring (correctness fix included)

The current conversion `event_pattern.replace('.', r'\.').replace('*', '.*')` produces unanchored patterns. `dataset.*` matches `dataset.changed` but also `any_prefix_dataset.changed`. Adding `^` and `$` anchors (as shown above) fixes this and is a correctness improvement, not just a performance one.

### 3. (Optional) Index patterns by prefix for O(1) dispatch

If the number of pattern subscribers grows large, a prefix-trie or prefix-bucket approach can reduce the scan further. For example, group patterns by their literal prefix before the first `*`:

```python
# "dataset.*" → prefix bucket "dataset"
# "chart.*"   → prefix bucket "chart"
```

On emit, only test patterns whose prefix matches the event type prefix. This reduces the scan to O(k) where k is the number of patterns matching the same prefix, which is typically 1–3.

This optimization is likely premature for the current codebase size but is worth noting for the future.

---

## Notes

- The current performance may not be measurable in normal usage (< 10 pattern subscribers). Profile before investing in the trie optimization.
- The pre-compilation fix (step 1) has zero downsides and should be done regardless.
- The anchoring fix (step 2) changes matching semantics slightly — verify that no existing subscriber relies on unanchored matching before deploying.
- Related: High #5 covers the structural duplication between `subscribe` and `unsubscribe` pattern conversion. Both issues should be fixed together in the same refactor.
