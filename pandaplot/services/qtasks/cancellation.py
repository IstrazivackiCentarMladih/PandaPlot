import threading


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
