import asyncio
import logging
from typing import Callable, Coroutine, TypeVar, Any
from functools import wraps

F = TypeVar("F", bound=Callable[..., Coroutine[Any, Any, Any]])

def retry(attempts: int = 3, delay: float = 1.0):
    """Retry an async function multiple times with a delay."""

    def decorator(func: F) -> F:
        @wraps(func)  # Preserve function metadata
        async def wrapper(*args, **kwargs):
            for i in range(attempts):
                try:
                    return await func(*args, **kwargs)
                except Exception as exc:  # pragma: no cover - logging
                    logging.debug(
                        "Attempt %s/%s failed: %s", i + 1, attempts, exc, exc_info=True
                    )
                    if i == attempts - 1:
                        raise
                    await asyncio.sleep(delay)

        return wrapper  # type: ignore[return-value]

    return decorator
