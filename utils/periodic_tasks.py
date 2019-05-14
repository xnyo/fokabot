import asyncio
import inspect
from typing import Callable

import logging

logger = logging.getLogger("periodic_task")


def periodic_task(seconds: int = 60) -> Callable:
    """
    Decorator that periodically awaits the decorated coroutine

    :param seconds: number of seconds between calls
    :return:
    """
    async def decorator(f: Callable) -> None:
        logger.debug(f"Started periodic job {f}")
        try:
            while True:
                await asyncio.sleep(seconds)
                try:
                    if inspect.iscoroutinefunction(f):
                        await f()
                    else:
                        f()
                except Exception as e:
                    logger.error(f"Unhandled exception in periodic task loop: {str(e)}")
                    # TODO: Sentry
        except asyncio.CancelledError:
            logger.info(f"Stopped periodic task {f}")
    return decorator
