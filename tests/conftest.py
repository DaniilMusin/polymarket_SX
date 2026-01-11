import asyncio
import os
import sys


if sys.platform == "win32":
    os.environ.setdefault("AIOHTTP_NO_AIODNS", "1")
    try:
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    except AttributeError:
        pass
