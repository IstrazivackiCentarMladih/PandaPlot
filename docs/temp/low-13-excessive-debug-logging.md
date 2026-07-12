# Low #13 — Excessive Debug Logging on Hot Paths

**Severity:** Low  
**File:** `pandaplot/models/events/event_bus.py`  
**Lines:** 72, 86–114

---

## Problem

`emit()` logs multiple `DEBUG`-level messages on every invocation, including after every event level in the hierarchy and a final summary:

```python
# event_bus.py:72
self.logger.debug("Emitting event: %s with data keys: %s", event_type, list(data.keys()))

# event_bus.py:107-109
if subscriber_count > 0 or pattern_matches > 0:
    self.logger.debug("Emitted event '%s' to %d direct subscribers and %d pattern matches",
                    event_level, subscriber_count, pattern_matches)

# event_bus.py:111-114
if total_callbacks_called == 0:
    self.logger.debug("Event '%s' emitted but no subscribers found", event_type)
else:
    self.logger.debug("Event '%s' completed: %d total callbacks executed", event_type, total_callbacks_called)
```

`subscribe()` and `unsubscribe()` also log on every call (lines 26, 32, 35, 44, 50, 56).

In production with `DEBUG` logging enabled, `emit()` is called on:
- Every cell edit in a dataset table.
- Every character typed in a note editor.
- Every chart property change.
- Every mouse move over a chart canvas (if progress events are routed through the bus).

Each such event fires `emit()` which triggers 3–5 debug log calls (one per hierarchy level + summary). With a fast typist editing a dataset, this can produce thousands of log lines per minute.

**The real cost is not the log lines themselves** (if logging to a file), but the **string formatting**. Even at `DEBUG` level, Python evaluates `list(data.keys())` on line 72 unconditionally — the `list()` call and key extraction happen even if `DEBUG` logging is disabled in the root logger. This is a well-known Python logging anti-pattern.

The current code does use `%`-style lazy formatting for most log calls (e.g., `"%s"` arguments are only interpolated if the message is actually emitted), which is correct. But `list(data.keys())` on line 72 is evaluated eagerly regardless of log level.

---

## Impact

- Minor CPU overhead on every `emit()` from the eager `list(data.keys())` evaluation.
- Log files grow rapidly when `DEBUG` is enabled, making it hard to find relevant entries.
- The high volume of debug messages makes actual errors and warnings harder to spot during development.

---

## Fix

### 1. Move eager expression inside the log call (or guard with `isEnabledFor`)

```python
# Before:
self.logger.debug("Emitting event: %s with data keys: %s", event_type, list(data.keys()))

# After (lazy — only evaluated if DEBUG is enabled):
if self.logger.isEnabledFor(logging.DEBUG):
    self.logger.debug("Emitting event: %s with data keys: %s", event_type, list(data.keys()))
```

Or restructure to avoid the `list()` call:

```python
self.logger.debug("Emitting event: %s", event_type)
```

The data keys add little diagnostic value for most debugging sessions.

### 2. Reduce per-hierarchy-level logging to a single summary

Replace the per-level log inside the hierarchy loop with a single post-loop summary:

```python
# Remove the per-level log inside the loop.
# After the loop:
self.logger.debug(
    "Event '%s' dispatched across %d levels: %d callbacks called",
    event_type, len(hierarchy), total_callbacks_called
)
```

### 3. Add a `TRACE` level or use `logging.DEBUG - 1` for the most verbose messages

If granular event tracing is genuinely useful for debugging, introduce a custom log level `TRACE = 5` (below `DEBUG = 10`) and log per-callback details there. This keeps `DEBUG` usable and `TRACE` opt-in:

```python
TRACE = 5
logging.addLevelName(TRACE, "TRACE")

# In emit():
self.logger.log(TRACE, "Callback called for event '%s': %s", event_level, callback)
```

---

## Notes

- This is the lowest priority item in the review — the impact is minor and only relevant when `DEBUG` logging is active (not in production with default `INFO` level).
- The fix in step 1 (guarding the `list()` call) is the only correctness concern. Steps 2 and 3 are quality-of-life improvements.
- Before changing log messages, check if any log-parsing tooling (scripts, monitoring) depends on the current message format.
