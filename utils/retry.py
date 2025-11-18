import asyncio
import logging
import random
from typing import Callable, Coroutine, TypeVar, Any, Tuple, Type, cast
from functools import wraps

F = TypeVar("F", bound=Callable[..., Coroutine[Any, Any, Any]])


def retry(
    attempts: int = 3,
    delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_backoff: bool = True,
    jitter: float = 0.1,
    exceptions: Tuple[Type[BaseException], ...] = (Exception,),
):
    """Retry an async function multiple times with exponential backoff and jitter.

    Parameters
    ----------
    attempts: int
        Number of attempts before giving up.
    delay: float
        Initial delay in seconds between retries.
    max_delay: float
        Maximum delay in seconds (caps exponential backoff).
    exponential_backoff: bool
        If True, use exponential backoff (delay * 2^attempt).
        If False, use fixed delay.
    jitter: float
        Random jitter factor (0-1) to add to delay to prevent thundering herd.
        Actual jitter = random(0, delay * jitter)
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

                    # Calculate delay with exponential backoff
                    if exponential_backoff:
                        current_delay = min(delay * (2 ** i), max_delay)
                    else:
                        current_delay = delay

                    # Add jitter to prevent thundering herd
                    if jitter > 0:
                        current_delay += random.uniform(0, current_delay * jitter)

                    logging.debug("Retrying in %.2f seconds...", current_delay)
                    await asyncio.sleep(current_delay)

        return cast(F, wrapper)

    return decorator
