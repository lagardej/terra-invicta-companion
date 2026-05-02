"""Decorator for logging function entry and/or exit."""

from __future__ import annotations

import functools
import inspect
import logging
from collections.abc import Callable, Coroutine
from typing import TypeVar

F = TypeVar("F", bound=Callable[..., object])


def log_call(
    level: int = logging.DEBUG,
    *,
    entry: bool = True,
    exit: bool = False,
    with_args: bool = False,
    with_result: bool = False,
) -> Callable[[F], F]:
    """Log a function call on entry and/or exit.

    Args:
        level: Logging level (default: DEBUG).
        entry: Log on function entry (default: True).
        exit: Log on function exit (default: False).
        with_args: Include args and kwargs in entry log (default: False).
        with_result: Include return value in exit log (default: False).

    Usage::

        @log_call(level=logging.INFO, exit=True, with_args=True)
        async def my_handler(self, event: MyEvent) -> None:
            ...
    """

    def decorator(fn: F) -> F:
        logger = logging.getLogger(fn.__module__)
        qualname = fn.__qualname__
        params = list(inspect.signature(fn).parameters)
        is_method = bool(params) and params[0] == "self"

        def _log_entry(args: tuple[object, ...], kwargs: dict[str, object]) -> None:
            if not entry:
                return
            if with_args:
                logged_args = args[1:] if is_method else args
                logger.log(
                    level, ">>> %s args=%s kwargs=%s", qualname, logged_args, kwargs
                )
            else:
                logger.log(level, ">>> %s", qualname)

        def _log_exit(result: object) -> None:
            if not exit:
                return
            if with_result:
                logger.log(level, "<<< %s returned %r", qualname, result)
            else:
                logger.log(level, "<<< %s", qualname)

        if inspect.iscoroutinefunction(fn):
            return _make_async_wrapper(fn, _log_entry, _log_exit)  # type: ignore[return-value]
        return _make_sync_wrapper(fn, _log_entry, _log_exit)  # type: ignore[return-value]

    return decorator


def _make_async_wrapper(
    fn: Callable[..., Coroutine[object, object, object]],
    log_entry: Callable[[tuple[object, ...], dict[str, object]], None],
    log_exit: Callable[[object], None],
) -> Callable[..., Coroutine[object, object, object]]:
    @functools.wraps(fn)
    async def wrapper(*args: object, **kwargs: object) -> object:
        log_entry(args, kwargs)
        result = await fn(*args, **kwargs)
        log_exit(result)
        return result

    return wrapper


def _make_sync_wrapper(
    fn: Callable[..., object],
    log_entry: Callable[[tuple[object, ...], dict[str, object]], None],
    log_exit: Callable[[object], None],
) -> Callable[..., object]:
    @functools.wraps(fn)
    def wrapper(*args: object, **kwargs: object) -> object:
        log_entry(args, kwargs)
        result = fn(*args, **kwargs)
        log_exit(result)
        return result

    return wrapper
