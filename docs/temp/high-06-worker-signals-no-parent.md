# High #6 — WorkerSignals Has No Qt Parent (Memory Leak)

**Severity:** High  
**File:** `pandaplot/services/qtasks/worker.py`  
**Lines:** 35  
**Related file:** `pandaplot/services/qtasks/worker_signal.py`

---

## Problem

`Worker.__init__` creates `WorkerSignals` as a standalone, parentless `QObject`:

```python
# worker.py:35
self.signals = WorkerSignals()
```

`WorkerSignals` itself does not accept a parent:

```python
# worker_signal.py:7
class WorkerSignals(QObject):
    finished = Signal()
    error = Signal(tuple)
    result = Signal(object)
    progress = Signal(float)
```

In Qt's memory model, `QObject` instances are freed when their parent is freed (parent-child tree). A `QObject` with no parent must be freed explicitly or by Python's garbage collector. Because `WorkerSignals` is a `QObject`, CPython's reference counting interacts with Qt's object management, and the two can disagree about when it's safe to free the object.

Concretely:
- `Worker` (a `QRunnable`) is managed by `QThreadPool`. With `autoDelete=True` (the default), Qt deletes the C++ side of `Worker` after `run()` returns.
- `Worker.signals` is a separate Python/C++ object with no connection to `Worker` in Qt's ownership tree.
- If `Worker`'s C++ side is deleted while the Python `Worker` object still exists (because something holds a Python reference), `worker.signals` is left dangling in the Qt object tree.
- Even without a crash, `WorkerSignals` is never garbage-collected until all Python references to it are dropped — but because signal connections hold references to callbacks, and callbacks may hold references back to `WorkerSignals` (directly or indirectly), circular references can form that Python's cyclic GC may not collect promptly.

---

## Impact

- `WorkerSignals` objects accumulate in memory across the session.
- Each leaked `WorkerSignals` also pins any connected callback (and anything the callback closes over) in memory.
- This is a compounding factor with Critical #1 (signals never disconnected): the two issues together guarantee leaks on every task execution.

---

## Fix

Make `Worker` the Qt parent of `WorkerSignals`:

```python
# worker_signal.py — accept optional parent
from PySide6.QtCore import QObject, Signal

class WorkerSignals(QObject):
    finished = Signal()
    error = Signal(tuple)
    result = Signal(object)
    progress = Signal(float)

    def __init__(self, parent: QObject | None = None):
        super().__init__(parent)
```

```python
# worker.py — pass self as parent
class Worker(QRunnable):
    def __init__(self, fn: WorkerFuncType, *args, **kwargs):
        super().__init__()
        self.fn = fn
        self.args = args
        self.kwargs = kwargs
        self.signals = WorkerSignals(parent=None)  # QRunnable is not a QObject, see note
        self.kwargs["progress_callback"] = self.signals.progress.emit
```

**Important caveat:** `QRunnable` does NOT inherit from `QObject`, so it cannot be a Qt parent. `WorkerSignals` cannot be parented to `Worker` directly through Qt's ownership tree.

The correct solution depends on the broader fix strategy:

### Option A — Move signals onto a QObject that is a real Qt parent

Extract the signals into a manager object that IS a `QObject` and IS owned by something with a clear lifetime (e.g., `TaskScheduler`, which is a regular Python object):

```python
class TaskHandle(QObject):
    """Owned by TaskScheduler; carries signals for one task."""
    finished = Signal()
    error = Signal(tuple)
    result = Signal(object)
    progress = Signal(float)

    def __init__(self, parent: QObject):
        super().__init__(parent)
```

`TaskScheduler` itself would need to be a `QObject` to serve as parent, or use a dedicated `QObject` owner.

### Option B — Explicit cleanup (simpler, pairs with Critical #1 fix)

If restructuring to use a `QObject` parent is too invasive, ensure that `WorkerSignals` is explicitly cleaned up after the task finishes. The Critical #1 fix (disconnecting all signals in `_finished_wrapper`) breaks the reference cycles. After all connections are removed, Python's GC can collect `WorkerSignals` normally:

```python
# After disconnecting all signals in _finished_wrapper:
worker.signals.deleteLater()  # schedule Qt-side deletion
```

`deleteLater()` posts a deferred deletion event to Qt's event loop, which is the safe way to delete a `QObject` from a non-GUI thread context.

---

## Notes

- The root cause is that `QRunnable` was chosen for thread execution (correct — it's lightweight) but it's not a `QObject`, which conflicts with the need to own a `QObject` (signals). This is a common Qt pain point.
- The cleanest long-term fix is Option A: make the signal carrier a `QObject` child of `TaskScheduler` (which should itself become a `QObject`). This aligns with Qt's recommended pattern for thread communication.
- This fix should be implemented alongside Critical #1 and Critical #2, as all three are symptoms of the same root cause: incomplete lifecycle management for worker objects.
