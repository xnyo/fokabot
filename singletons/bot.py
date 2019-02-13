import asyncio
import functools
import logging
from typing import Callable, Optional

from bottom import Client

from utils import singleton


@singleton.singleton
class Bot:
    def __init__(self, *, host: str = "irc.ripple.moe", port: int = 6667, ssl: bool = True, nickname: str = "FokaBot", password: str=""):
        self.client: Client = Client(host, port, ssl=ssl)
        self.nickname = nickname
        self.password = password
        self.logger = logging.getLogger("fokabot")
        self.logger.info(f"Creating bot ({self.nickname}) {host}:{port} (ssl: {ssl})")
        self.joined_channels = set()
        self.command_handlers = {}
        self.command_prefix = "!"   # TODO: configurable
        self.ready = False

    @property
    def loop(self):
        return self.client.loop

    def run(self):
        self.loop.create_task(self.client.connect())
        self.client.loop.run_forever()

    @staticmethod
    def waiter(client):
        async def wait_for(*events, return_when=asyncio.FIRST_COMPLETED):
            if not events:
                return
            done, pending = await asyncio.wait(
                [client.wait(event) for event in events],
                loop=client.loop,
                return_when=return_when
            )

            # Get the result(s) of the completed task(s).
            ret = [future.result() for future in done]

            # Cancel any events that didn't come in.
            for future in pending:
                future.cancel()

            # Return list of completed event names.
            return ret
        return wait_for

    @property
    def wait_for(self):
        return self.waiter(self.client)

    def command(self, event: str, func: Optional[Callable] = None) -> Callable:
        if func is None:
            return functools.partial(self.command, event)  # type: ignore
        wrapped = func
        if not asyncio.iscoroutinefunction(wrapped):
            wrapped = asyncio.coroutine(wrapped)
        self.command_handlers[event.lower()] = wrapped
        # Always return original
        return func
