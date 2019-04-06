import asyncio
import functools
import logging
from typing import Callable, Optional, Dict

from bottom import Client

from utils import singleton
from utils.rippleapi import BanchoApiClient, RippleApiClient


@singleton.singleton
class Bot:
    def __init__(
        self, *, host: str = "irc.ripple.moe", port: int = 6667,
        ssl: bool = True, nickname: str = "FokaBot", password: str = "",
        commands_prefix: str = "!", bancho_api_client: BanchoApiClient = None,
        ripple_api_client: RippleApiClient = None
    ):
        """
        Initializes Fokabot

        :param host: IRC server host
        :param port: IRC server port
        :param ssl: whether the IRC server supports SSL or not
        :param nickname: bot nickname
        :param password: bot password ("irc token")
        :param commands_prefix: commands prefix (eg: !, ;, ...)
        """
        self.client: Client = Client(host, port, ssl=ssl)
        self.bancho_api_client = bancho_api_client
        self.ripple_api_client = ripple_api_client
        if self.bancho_api_client is None or type(self.bancho_api_client) is not BanchoApiClient:
            raise RuntimeError("You must provide a valid BanchoApiClient")
        self.nickname = nickname
        self.password = password
        self.logger = logging.getLogger("fokabot")
        self.logger.info(f"Creating bot ({self.nickname}) {host}:{port} (ssl: {ssl})")
        if not ssl:
            self.logger.warning("SSL is disabled")
        self.joined_channels = set()
        self.command_handlers: Dict[str, Callable] = {}
        self.command_prefix = commands_prefix
        self.ready = False

    @property
    def loop(self) -> asyncio.AbstractEventLoop:
        """
        Returns the IRC client IOLoop

        :return: the IOLoop
        """
        return self.client.loop

    def run(self) -> None:
        """
        Connects the IRC client and runs its loop forever

        :return:
        """
        self.loop.create_task(self.client.connect())
        self.client.loop.run_forever()

    def _waiter(self) -> Callable:
        """
        Helper for self.wait_for

        :return:
        """
        async def wait_for(*events, return_when=asyncio.FIRST_COMPLETED):
            if not events:
                return
            done, pending = await asyncio.wait(
                [self.client.wait(event) for event in events],
                loop=self.client.loop,
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
    def wait_for(self) -> Callable:
        """
        Waits for a (or some) specific IRC response(s)
        ```
        >>> # awaits RPL_ENDOFMOTD
        >>> await bot.wait_for("RPL_ENDOFMOTD")
        >>>
        >>> # awaits RPL_ENDOFMOTD and gets the response
        >>> end_of_motd = await bot.wait_for("RPL_ENDOFMOTD")
        >>>
        >>> # awaits for either RPL_ENDOFMOTD or ERR_NOMOTD and gets only response for ERR_NOMOTD
        >>> _, no_motd = await bot.wait_for("RPL_ENDOFMOTD", "ERR_NOMOTD")
        ```

        :return:
        """
        return self._waiter()

    def command(self, command_name: str, func: Optional[Callable] = None) -> Callable:
        """
        Registers a new command (decorator)
        ```
        >>> @bot.command("roll")
        >>> @base
        >>> async def roll_handler(username: str, channel: str) -> str:
        >>>     return "response"
        ```

        :param command_name: command name
        :param func: function to call. Must accept two arguments (username, channel) and return a str or None.
        :return:
        """
        if func is None:
            return functools.partial(self.command, command_name)  # type: ignore
        wrapped = func
        if not asyncio.iscoroutinefunction(wrapped):
            wrapped = asyncio.coroutine(wrapped)
        self.command_handlers[command_name.lower()] = wrapped
        # Always return original
        return func
