import asyncio
import signal
from asyncio import Queue

import functools
import logging
from typing import Callable, Optional, Dict, Union, List, Tuple

from aiohttp import web

from bottom import Client

from utils import singleton
from utils.letsapi import LetsApiClient
from utils.np_storage import NpStorage
from utils.periodic_tasks import periodic_task
from utils.privileges_cache import PrivilegesCache
from utils.rippleapi import BanchoApiClient, RippleApiClient


@singleton.singleton
class Bot:
    VERSION: str = "2.0.0"

    def __init__(
        self, *, host: str = "irc.ripple.moe", port: int = 6667,
        ssl: bool = True, nickname: str = "FokaBot", password: str = "",
        commands_prefix: str = "!",
        bancho_api_client: BanchoApiClient = None,
        ripple_api_client: RippleApiClient = None,
        lets_api_client: LetsApiClient = None,
        http_host: str = None, http_port: int = None
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
        self.http_host = http_host
        self.http_port = http_port
        self.client: Client = Client(host, port, ssl=ssl)
        self.bancho_api_client = bancho_api_client
        self.ripple_api_client = ripple_api_client
        self.lets_api_client = lets_api_client
        self.web_app: web.Application = web.Application()
        self.privileges_cache: PrivilegesCache = PrivilegesCache(self.ripple_api_client)
        self.np_storage: NpStorage = NpStorage()
        self.periodic_tasks: List[asyncio.Task] = []
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
        self.action_handlers: Dict[str, Callable] = {}
        self.command_prefix = commands_prefix
        self._ready = self.ready = False
        self.reconnecting = False
        self.disposing = False

        self.login_channels_queue = Queue()
        self.login_channels_left = set()

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
        import internal_api.handlers
        self.web_app.add_routes([
            web.post("/api/v0/send_message", internal_api.handlers.send_message)
        ])
        api_runner = web.AppRunner(self.web_app)
        self.loop.run_until_complete(api_runner.setup())
        site = web.TCPSite(api_runner, self.http_host, self.http_port)
        asyncio.ensure_future(site.start())
        self.periodic_tasks.extend(
            (
                self.loop.create_task(periodic_task(seconds=60)(self.privileges_cache.purge)),
                self.loop.create_task(periodic_task(seconds=60)(self.np_storage.purge))
            )
        )

        self.loop.create_task(self.client.connect())
        signal.signal(signal.SIGINT, lambda s, f: self.loop.stop())
        try:
            self.loop.run_forever()
        finally:
            self.logger.info("Interrupted.")
            self.loop.run_until_complete(self.dispose())
            self.loop.stop()
            self.logger.info("Goodbye!")

    async def dispose(self):
        """
        Sends QUIT to the server and disconnects the client

        :return:
        """
        self.disposing = True
        for task in self.periodic_tasks:
            task.cancel()
        self.logger.info("Disposing Fokabot")
        self.client.send("QUIT")
        await self.client.disconnect()

    def _waiter(self) -> Callable:
        """
        Helper for self.wait_for

        :return:
        """
        async def wait_for(*events, return_when=asyncio.FIRST_COMPLETED):
            self.logger.debug(f"Waiting for {events}")
            if not events:
                return
            done, pending = await asyncio.wait(
                [self.client.wait(event) for event in events],
                loop=self.loop,
                return_when=return_when
            )
            self.logger.debug(f"Got something (done:{done}, pending:{pending})")

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

    def command(
        self, command_name: Union[str, List[str], Tuple[str]], action: bool = False, func: Optional[Callable] = None
    ) -> Callable:
        """
        Registers a new command (decorator)
        ```
        >>> @bot.command("roll")
        >>> @base
        >>> async def roll_handler(username: str, channel: str) -> str:
        >>>     return "response"
        ```

        :param command_name: command name
        :param action: if True, the command "x" will be triggered when "\x01ACTION x" is sent.
        :param func: function to call. Must accept two arguments (username, channel) and return a str or None.
        :return:
        """
        if func is None:
            return functools.partial(self.command, command_name, action)  # type: ignore
        import plugins
        wrapped = plugins.base(func)
        if not asyncio.iscoroutinefunction(wrapped):
            wrapped = asyncio.coroutine(wrapped)
        if type(command_name) not in (list, tuple):
            command_name = (command_name,)
        for c in command_name:
            (self.action_handlers if action else self.command_handlers)[c.lower()] = wrapped
        # Always return original
        return functools.partial(func, command_name=command_name)

    @property
    def ready(self) -> bool:
        """
        Whether the bot is ready to process requests
        (it has logged in and it has joined all channels)

        :return: whether the bot is ready or not
        """
        return self._ready

    @ready.setter
    def ready(self, value: bool) -> None:
        """
        Sets the "ready" flag.
        If setting to True, it'll trigger the 'ready' event on the IRC bot as well.

        :param value: new "ready" flag value
        :return:
        """
        self._ready = value
        if self.ready:
            self.client.trigger("ready")

    def reset(self) -> None:
        """
        Resets the bot. Must be called when reconnecting.
        (Sets ready to False, clears joined channels set, empties the login channels queue)

        :return:
        """
        self.ready = False
        self.joined_channels.clear()
        while not self.login_channels_queue.empty():
            self.login_channels_queue.get_nowait()
        self.login_channels_left.clear()
