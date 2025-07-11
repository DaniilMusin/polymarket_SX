import asyncio
import pytest

from utils.retry import retry

class CustomError(Exception):
    pass

class OtherError(Exception):
    pass

@pytest.mark.asyncio
async def test_retry_only_selected_exceptions():
    attempts = 0

    @retry(attempts=3, delay=0, exceptions=(CustomError,))
    async def _func():
        nonlocal attempts
        attempts += 1
        raise OtherError("boom")

    with pytest.raises(OtherError):
        await _func()

    assert attempts == 1


@pytest.mark.asyncio
async def test_retry_retries_matching_exception():
    attempts = 0

    @retry(attempts=3, delay=0, exceptions=(CustomError,))
    async def _func():
        nonlocal attempts
        attempts += 1
        raise CustomError("boom")

    with pytest.raises(CustomError):
        await _func()

    assert attempts == 3
