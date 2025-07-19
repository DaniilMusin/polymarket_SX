import asyncio
import logging
from typing import Callable, Coroutine, TypeVar, Any, Tuple, Type, cast
from functools import wraps

F = TypeVar("F", bound=Callable[..., Coroutine[Any, Any, Any]])


def retry(
    attempts: int = 3,
    delay: float = 1.0,
    exceptions: Tuple[Type[BaseException], ...] = (Exception,),
):
    """Retry an async function multiple times with a delay.

    Parameters
    ----------
    attempts: int
        Number of attempts before giving up.
    delay: float
        Delay in seconds between retries.
    exceptions: tuple[type[BaseException], ...]
        Exception types that trigger a retry.
    """

    def decorator(func: F) -> F:
        @wraps(func)  # Preserve function metadata
        async def wrapper(*args, **kwargs):
            for i in range(attempts):
                try:
                    return await func(*args, **kwargs)
                except Exception as exc:  # pragma: no cover - logging
                    if not isinstance(exc, exceptions):
                        raise
                    logging.debug(
                        "Attempt %s/%s failed: %s", i + 1, attempts, exc, exc_info=True
                    )
                    if i == attempts - 1:
                        raise
                    await asyncio.sleep(delay)

        return cast(F, wrapper)

    return decorator
