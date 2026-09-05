"""Shared fixtures for command tests that dispatch work via TaskScheduler."""

import inspect
import traceback
from typing import Any, Callable, Optional, Union

import pytest

from pandaplot.services.qtasks.cancellation import CancellationToken, TaskCancelledError


class SyncTaskScheduler:
    """Drop-in TaskScheduler replacement that runs the task synchronously,
    inline, instead of on a QThreadPool thread. Mirrors Worker.run()'s
    try/except/else/finally shape exactly so command code under test behaves
    identically to production, just without real threading."""

    def __init__(self) -> None:
        self._active_tokens: list[tuple[Callable[..., Any], CancellationToken]] = []

    def run_task(
        self,
        task: Callable[..., Any],
        task_arguments: Optional[dict] = None,
        on_result: Optional[Callable[[Any], None]] = None,
        on_error: Optional[Callable[[tuple], None]] = None,
        on_finished: Optional[Callable[[], None]] = None,
        on_progress: Optional[Callable[[float], None]] = None,
        on_cancelled: Optional[Callable[[], None]] = None,
        cancellation_token: Optional[CancellationToken] = None,
    ) -> CancellationToken:
        task_arguments = task_arguments if task_arguments is not None else {}
        token = cancellation_token or CancellationToken()
        self._active_tokens.append((task, token))

        progress_callback = on_progress if on_progress is not None else (lambda _p: None)
        extra_kwargs = {}

        try:
            sig = inspect.signature(task)
            params = sig.parameters
            has_var_keyword = any(p.kind == inspect.Parameter.VAR_KEYWORD for p in params.values())
            if "is_cancelled" in params or has_var_keyword:
                extra_kwargs["is_cancelled"] = token.is_cancelled
            if "cancellation_token" in params or has_var_keyword:
                extra_kwargs["cancellation_token"] = token
        except (ValueError, TypeError):
            pass

        all_kwargs = {**task_arguments, "progress_callback": progress_callback, **extra_kwargs}

        if token.is_cancelled():
            if on_cancelled:
                on_cancelled()
            if on_finished:
                on_finished()
            return token

        try:
            result = task(**all_kwargs)
            if token.is_cancelled():
                raise TaskCancelledError("Task was cancelled.")
        except TaskCancelledError:
            if on_cancelled:
                on_cancelled()
        except Exception as e:
            if token.is_cancelled():
                if on_cancelled:
                    on_cancelled()
            elif on_error:
                on_error((type(e), e, traceback.format_exc()))
        else:
            if on_result:
                on_result(result)
        finally:
            if on_finished:
                on_finished()

        return token

    def cancel_task(self, task_or_token: Union[Callable[..., Any], CancellationToken]) -> bool:
        cancelled_any = False
        for fn, token in list(self._active_tokens):
            if token == task_or_token or fn == task_or_token:
                token.cancel()
                cancelled_any = True
        return cancelled_any

    def cancel_all(self) -> None:
        for _fn, token in list(self._active_tokens):
            token.cancel()


@pytest.fixture
def sync_task_scheduler():
    return SyncTaskScheduler()
