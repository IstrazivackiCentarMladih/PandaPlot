import inspect
import threading
from typing import Any, Callable, Dict


class TaskCancelledError(Exception):
    """Exception raised when a task is cancelled during execution."""

    pass


class CancellationToken:
    """Cooperative cancellation token for background tasks.

    Thread-safe flag that can be checked by task functions or polled/called
    to determine if cancellation was requested.
    """

    def __init__(self) -> None:
        self._cancelled = False
        self._lock = threading.Lock()

    def cancel(self) -> None:
        """Request cancellation."""
        with self._lock:
            self._cancelled = True

    def is_cancelled(self) -> bool:
        """Return True if cancellation has been requested."""
        with self._lock:
            return self._cancelled

    def __call__(self) -> bool:
        """Callable shorthand for is_cancelled()."""
        return self.is_cancelled()

    def raise_if_cancelled(self) -> None:
        """Raise TaskCancelledError if cancellation has been requested."""
        if self.is_cancelled():
            raise TaskCancelledError("Task was cancelled.")


def build_cancellation_kwargs(fn: Callable[..., Any], token: CancellationToken) -> Dict[str, Any]:
    """Inspect fn's signature and return the is_cancelled/cancellation_token
    kwargs it should be called with, based on which of them it declares (or,
    if it accepts **kwargs, both).
    """
    try:
        params = inspect.signature(fn).parameters
    except (ValueError, TypeError):
        # fn is a built-in or C-extension without signature support.
        return {}

    has_var_keyword = any(p.kind == inspect.Parameter.VAR_KEYWORD for p in params.values())

    kwargs: Dict[str, Any] = {}
    if "is_cancelled" in params or has_var_keyword:
        kwargs["is_cancelled"] = token.is_cancelled
    if "cancellation_token" in params or has_var_keyword:
        kwargs["cancellation_token"] = token
    return kwargs
