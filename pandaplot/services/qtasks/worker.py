import inspect
import sys
import traceback
from typing import Any, Callable, Optional, Protocol

from PySide6.QtCore import (
    QRunnable,
    Slot,
)

from pandaplot.services.qtasks.cancellation import CancellationToken, TaskCancelledError
from pandaplot.services.qtasks.worker_signal import WorkerSignals


class WorkerFuncType(Protocol):
    def __call__(self, progress_callback: Callable[[float], None], *args: Any, **kwargs: Any) -> Any: ...


class Worker(QRunnable):
    """Worker thread.

    Inherits from QRunnable to handle worker thread setup, signals and wrap-up.

    :param fn: The function callback to run on this worker thread.
    :param cancellation_token: Optional CancellationToken instance to track task cancellation.
    :param args: Arguments to pass to the callback function
    :param kwargs: Keywords to pass to the callback function
    """

    def __init__(self, fn: WorkerFuncType, cancellation_token: Optional[CancellationToken] = None, *args, **kwargs):
        super().__init__()
        self.fn = fn
        self.cancellation_token = cancellation_token or CancellationToken()
        self.args = args
        self.kwargs = kwargs
        self.signals = WorkerSignals()

        # Add progress_callback
        self.kwargs["progress_callback"] = self.signals.progress.emit

        # Inspect fn signature to supply cancellation tokens if accepted or if **kwargs accepted
        try:
            sig = inspect.signature(fn)
            params = sig.parameters
            has_var_keyword = any(p.kind == inspect.Parameter.VAR_KEYWORD for p in params.values())

            if "is_cancelled" in params or has_var_keyword:
                self.kwargs["is_cancelled"] = self.cancellation_token.is_cancelled
            if "cancellation_token" in params or has_var_keyword:
                self.kwargs["cancellation_token"] = self.cancellation_token
        except (ValueError, TypeError):
            # In case fn is a built-in or C-extension without signature support
            pass

    @Slot()
    def run(self):
        if self.cancellation_token.is_cancelled():
            self.signals.cancelled.emit()
            self.signals.finished.emit()
            return

        try:
            result = self.fn(*self.args, **self.kwargs)
            if self.cancellation_token.is_cancelled():
                raise TaskCancelledError("Task was cancelled.")
        except TaskCancelledError:
            self.signals.cancelled.emit()
        except Exception:
            if self.cancellation_token.is_cancelled():
                self.signals.cancelled.emit()
            else:
                traceback.print_exc()
                exctype, value = sys.exc_info()[:2]
                self.signals.error.emit((exctype, value, traceback.format_exc()))
        else:
            self.signals.result.emit(result)
        finally:
            self.signals.finished.emit()
