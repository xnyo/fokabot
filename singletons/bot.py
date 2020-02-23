import asyncio
import inspect
import signal
import sys

import plugins.base
from utils.beatconnect_api import BeatconnectAPIClient
from utils.init_hook import InitHook
from utils.osuapi import OsuAPIClient
from ws.client import WsClient
from ws.messages import WsChatMessage

try:
    import ujson as json
except ImportError:
    import json

import functools
import logging
from typing import Callable, Optional, Dict, Union, List, Tuple, Type, Iterator, Generator, Iterable, Set

from aiohttp import web
import aioredis

from pubsub import reader
from pubsub.manager import PubSubBindingManager
from utils import singleton
from utils.letsapi import LetsApiClient
from utils.np_storage import NpStorage
from utils.periodic_tasks import periodic_task
from utils.rippleapi import BanchoApiClient, RippleApiClient, CheesegullApiClient
from constants.api_privileges import APIPrivileges


@singleton.singleton
class Bot:
    VERSION: str = "2.3.0"

    def __init__(
        self, *, nickname: str = "FokaBot", wss: bool = True,
        commands_prefix: str = "!",
        bancho_api_client: BanchoApiClient = None,
        ripple_api_client: RippleApiClient = None,
        cheesegull_api_client: CheesegullApiClient = None,
        lets_api_client: LetsApiClient = None,
        osu_api_client: OsuAPIClient = None,
        beatconnect_api_client: BeatconnectAPIClient = None,
        http_host: str = None, http_port: int = None,
        redis_host: str = "127.0.0.1", redis_port: int = 6379,
        redis_database: int = 0, redis_password: Optional[str] = None,
        redis_pool_size: int = 8,
    ):
        self.ready = False
        self.nickname = nickname
        self.http_host = http_host
        self.http_port = http_port

        # Viviamo in un mondo di API 🐝🐝🐝 (cit)
        self.bancho_api_client = bancho_api_client
        self.ripple_api_client = ripple_api_client
        self.cheesegull_api_client = cheesegull_api_client
        self.osu_api_client = osu_api_client
        self.lets_api_client = lets_api_client
        self.beatconnect_api_client = beatconnect_api_client

        self.web_app: web.Application = web.Application()
        # self.privileges_cache: PrivilegesCache = PrivilegesCache(self.ripple_api_client)
        self.np_storage: NpStorage = NpStorage()
        self.periodic_tasks: List[asyncio.Task] = []
        if self.bancho_api_client is None or type(self.bancho_api_client) is not BanchoApiClient:
            raise RuntimeError("You must provide a valid BanchoApiClient")
        self.logger = logging.getLogger("fokabot")
        self.wss = wss
        if not wss:
            self.logger.warning("WSS is disabled")
        self.command_handlers: Dict[str, plugins.base.Command] = {}
        self.action_handlers: Dict[str, plugins.base.Command] = {}
        self.command_prefix = commands_prefix
        self.reconnecting = False
        self.disposing = False
        endpoint_base = self.bancho_api_client.base.rstrip('/')
        for x in ("http://", "https://"):
            if endpoint_base.startswith(x):
                endpoint_base = endpoint_base[len(x):]
        self.client = WsClient(
            f"{'wss' if self.wss else 'ws'}://{endpoint_base}/api/v2/ws"
        )

        self.redis_host = redis_host
        self.redis_port = redis_port
        self.redis_database = redis_database
        self.redis_password = redis_password
        self.redis_pool_size = redis_pool_size
        self._pubsub_task: Optional[asyncio.Task] = None
        self.pubsub_binding_manager: PubSubBindingManager = PubSubBindingManager()

        self.login_channels_left: Set[str] = set()
        self.joined_channels: Set[str] = set()
        self.match_delayed_start_tasks: Dict[int, asyncio.Task] = {}
        self.init_hooks: List[InitHook] = []

    def send_message(self, message: str, recipient: str) -> None:
        """
        Shorthand to send a message

        :param message:
        :param recipient:
        :return:
        """
        self.client.send(WsChatMessage(message, recipient))

    @property
    def loop(self) -> asyncio.AbstractEventLoop:
        return asyncio.get_event_loop()

    async def run_init_hooks(self) -> None:
        """
        Runs all registered init hooks.

        :return:
        """
        self.logger.info("Running init hooks")
        for hook in self.init_hooks:
            self.logger.info(f"Running init hook for plugin {hook.plugin}")
            await hook.func() if inspect.iscoroutinefunction(hook.func) else hook.func()

    def run(self) -> None:
        """
        Connects the ws and runs its loop forever.
        Starts the internal api and the periodic tasks as well.

        :return:
        """
        import internal_api.handlers

        try:
            asyncio.get_event_loop().run_until_complete(self._check_api_keys())
        except RuntimeError as e:
            logging.error(e)
            sys.exit(-1)

        self.web_app.add_routes([
            web.post("/api/v0/send_message", internal_api.handlers.send_message)
        ])
        api_runner = web.AppRunner(self.web_app)
        self.loop.run_until_complete(api_runner.setup())
        site = web.TCPSite(api_runner, self.http_host, self.http_port)
        asyncio.ensure_future(site.start())

        asyncio.get_event_loop().run_until_complete(self._initialize_redis())
        self.periodic_tasks.extend(
            (
                # self.loop.create_task(periodic_task(seconds=60)(self.privileges_cache.purge)),
                self.loop.create_task(periodic_task(seconds=60)(self.np_storage.purge)),
            )
        )

        asyncio.get_event_loop().run_until_complete(self._initialize_ws())

        def term():
            self.loop.stop()

        self.loop.add_signal_handler(signal.SIGINT, term)
        self.loop.add_signal_handler(signal.SIGTERM, term)

        try:
            self.loop.run_forever()
        finally:
            self.logger.info("Interrupted.")
            self.loop.run_until_complete(self.dispose())
            self.loop.stop()
            self.logger.info("Komm Süsser Tod.")

    async def dispose(self):
        """
        Sends QUIT to the server and disconnects the client

        :return:
        """
        self.logger.info("Disposing Fokabot")
        self.disposing = True

        self.logger.info("Disposing periodic tasks")
        for task in self.periodic_tasks:
            task.cancel()

        self.logger.info("Disposing redis")
        self.redis.close()
        await self.redis.wait_closed()
        if self._pubsub_task is not None:
            self._pubsub_task.cancel()

        # Close ws connetion
        try:
            if self.client.running:
                self.logger.info("Closing ws connection")
                self.client.stop()
                await self.client.wait("disconnected")
        except Exception as e:
            self.logger.error(f"Error while closing ws connection ({e})")

    def command(
        self, command_name: Union[str, List[str], Tuple[str]],
        action: bool = False, func: Optional[Callable] = None
    ) -> Callable:
        """
        Registers a new command (decorator)
        ```
        >>> @bot.command("hello")
        >>> @plugins.base
        >>> async def hello() -> str:
        >>>     return "hi!"
        ```

        :param command_name: command name
        :param action: if True, the command "x" will be triggered when "\x01ACTION x" is sent.
        :param func: function to call. Must accept two arguments (username, channel) and return a str or None.
        :return:
        """
        if func is None:
            return functools.partial(self.command, command_name, action)  # type: ignore
        wrapped = plugins.base.errors(func)
        if not asyncio.iscoroutinefunction(wrapped):
            wrapped = asyncio.coroutine(wrapped)
        if type(command_name) not in (list, tuple):
            command_name = (command_name,)
        command_name = tuple(x.lower() for x in command_name)
        dest = self.action_handlers if action else self.command_handlers
        dest[command_name[0]] = plugins.base.CommandWrapper(command_name[0], wrapped, aliases=command_name[1:])
        for alias in command_name[1:]:
            dest[alias] = plugins.base.CommandAlias(alias, wrapped, root_name=command_name[0])
        # Always return original
        return functools.partial(func, command_name=command_name)

    def get_commands_with_prefix(self, prefix: str) -> Iterator[Tuple[str, plugins.base.Command]]:
        """
        Returns a list with all commands that start with a specific prefix.

        :param prefix: the prefix, not including the bot prefix. eg: 'mp'
        :return: a list of all commands that start with that prefix
        """
        for k, v in self.command_handlers.items():
            if k.startswith(prefix):
                yield k, v

    def reset(self) -> None:
        """
        Resets the bot. Must be called when reconnecting.
        (Sets ready to False, clears joined channels set, empties the login channels queue)

        :return:
        """
        self.ready = False
        self.login_channels_left.clear()
        self.joined_channels.clear()

    async def _initialize_pubsub(self) -> None:
        import pubsub.handlers.message

        self.logger.debug("Subscribing to redis pubsub")
        channels = await self.redis.psubscribe("fokabot:*")
        if len(channels) != 1:
            self.logger.error("Invalid Redis pubsub channels!")
            return
        self.logger.info("Subscribed to redis pubsub channels")

        # Start the reader (hangs)
        await reader(channels[0])

    async def _initialize_redis(self) -> None:
        """
        Connects to redis

        :return:
        """
        self.redis = await aioredis.create_redis_pool(
            address=(self.redis_host, self.redis_port),
            db=self.redis_database,
            password=self.redis_password,
            maxsize=self.redis_pool_size
        )
        self._pubsub_task = asyncio.ensure_future(self._initialize_pubsub())
        self.logger.info("Connected to Redis")

    async def _initialize_ws(self) -> None:
        self.logger.debug("Starting ws client")
        try:
            await self.client.start()
        except ConnectionError as e:
            self.logger.error(f"{e}. Now disposing.")
            self.loop.stop()

    async def _check_api_keys(self) -> None:
        for name, client, expected in (
            ("Ripple", self.ripple_api_client, APIPrivileges.all_privileges() & ~APIPrivileges.BANCHO),
            ("Delta", RippleApiClient(
                self.bancho_api_client.token,
                self.ripple_api_client.base
            ), APIPrivileges.all_privileges())
        ):
            self.logger.info(f"Checking {name} API key")
            r = await client.ping()
            actual = APIPrivileges(r.get("privileges", APIPrivileges.NONE))
            self.logger.debug(f"{name} api key privileges: {actual}, expected {expected}")
            if not actual.has(expected):
                raise RuntimeError(
                    f"The provided {name} API key doesn't have the required privileges. "
                    f"Expected {expected}, got {actual}."
                )
