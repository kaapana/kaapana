import asyncio
import logging
from asyncio import ensure_future
from functools import wraps
from traceback import format_exception
from typing import Any, Callable, Coroutine, Optional, Union

from filelock import FileLock, Timeout
from starlette.concurrency import run_in_threadpool

NoArgsNoReturnFuncT = Callable[[], None]
NoArgsNoReturnAsyncFuncT = Callable[[], Coroutine[Any, Any, None]]
NoArgsNoReturnDecorator = Callable[
    [Union[NoArgsNoReturnFuncT, NoArgsNoReturnAsyncFuncT]], NoArgsNoReturnAsyncFuncT
]


# Source: https://github.com/dmontagu/fastapi-utils/blob/master/fastapi_utils/tasks.py
# Docu: https://fastapi-utils.davidmontague.xyz/user-guide/repeated-tasks/
def repeat_every(
    *,
    seconds: float,
    wait_first: bool = False,
    logger: Optional[logging.Logger] = None,
    raise_exceptions: bool = False,
    max_repetitions: Optional[int] = None,
) -> NoArgsNoReturnDecorator:
    """
    This function returns a decorator that modifies a function so it is periodically re-executed after its first call.
    The function it decorates should accept no arguments and return nothing. If necessary, this can be accomplished
    by using `functools.partial` or otherwise wrapping the target function prior to decoration.
    Parameters
    ----------
    seconds: float
        The number of seconds to wait between repeated calls
    wait_first: bool (default False)
        If True, the function will wait for a single period before the first call
    logger: Optional[logging.Logger] (default None)
        The logger to use to log any exceptions raised by calls to the decorated function.
        If not provided, exceptions will not be logged by this function (though they may be handled by the event loop).
    raise_exceptions: bool (default False)
        If True, errors raised by the decorated function will be raised to the event loop's exception handler.
        Note that if an error is raised, the repeated execution will stop.
        Otherwise, exceptions are just logged and the execution continues to repeat.
        See https://docs.python.org/3/library/asyncio-eventloop.html#asyncio.loop.set_exception_handler for more info.
    max_repetitions: Optional[int] (default None)
        The maximum number of times to call the repeated function. If `None`, the function is repeated forever.
    """

    def decorator(
        func: Union[NoArgsNoReturnAsyncFuncT, NoArgsNoReturnFuncT],
    ) -> NoArgsNoReturnAsyncFuncT:
        """
        Converts the decorated function into a repeated, periodically-called version of itself.
        """
        is_coroutine = asyncio.iscoroutinefunction(func)

        @wraps(func)
        async def wrapped() -> None:
            repetitions = 0

            async def loop() -> None:
                nonlocal repetitions
                if wait_first:
                    await asyncio.sleep(seconds)
                while max_repetitions is None or repetitions < max_repetitions:
                    try:
                        if is_coroutine:
                            await func()  # type: ignore
                        else:
                            await run_in_threadpool(func)
                        repetitions += 1
                    except Exception as exc:
                        if logger is not None:
                            formatted_exception = "".join(
                                format_exception(type(exc), exc, exc.__traceback__)
                            )
                            logger.error(formatted_exception)
                        if raise_exceptions:
                            raise exc
                    await asyncio.sleep(seconds)

            ensure_future(loop())

        return wrapped

    return decorator


def only_one_process(lock_file="/tmp/airflow_sync.lock"):
    """
    This decorator is used for the syncing functions in main.py.
    It prevents multiple workers syncing the database with the airflow and creating duplicates.
    It uses filesystem lock.


    Note: Previous implementation allow only first child Worker to sync, however it could get stuck,
    if only second was chosen but was not permitted to work on the sync. (It was hard to debug in dev-mode)

    Args:
        func (function): function to be decorated
    """

    def inner(func):
        def wrapper(*args, **kwargs):
            lock = FileLock(lock_file, timeout=0)
            try:
                with lock:
                    logging.debug(f"Acquired lock for {func.__name__}")
                    return func(*args, **kwargs)
            except Timeout:
                logging.debug(f"Another process is already handling {func.__name__}.")

        return wrapper

    return inner
