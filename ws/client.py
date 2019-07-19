import functools
import logging

import asyncio
from collections import defaultdict
from typing import Optional, List, Callable, DefaultDict

import traceback

try:
    import ujson as json
except ImportError:
    import json
import json as stdjson

import aiohttp

from ws.messages import WsMessage


class LoginFailedError(Exception):
    pass


class WsClient:
    logger = logging.getLogger("ws_client")

    def __init__(self, ws_url: str):
        self.ws_url = ws_url
        self._reader_queue = asyncio.Queue()
        self._writer_queue = asyncio.Queue()
        self._events: DefaultDict[str, asyncio.Event] = defaultdict(lambda: asyncio.Event())
        self._event_handlers: DefaultDict[str, List[Callable]] = defaultdict(list)
        self.ws: Optional[aiohttp.ClientWebSocketResponse] = None
        self.writer_task: Optional[asyncio.Task] = None
        self.reader_task: Optional[asyncio.Task] = None
        self.running: bool = False

    def send(self, message: WsMessage) -> None:
        self._writer_queue.put_nowait(message)

    @staticmethod
    def decode_message(message: aiohttp.WSMessage) -> WsMessage:
        try:
            json_message = json.loads(message.data)
        except (stdjson.JSONDecodeError, ValueError) as e:
            # ujson uses ValueError and doesn't have JSONDecodeError
            # so we must import both ujson and json (or json twice)
            raise ValueError()
        return WsMessage.dict_factory(json_message)

    async def writer(self):
        try:
            self.logger.debug("Started writer task")
            while True:
                message = await self._writer_queue.get()
                if message is None:
                    self.logger.debug("Writer: Ignored a None message")
                    continue
                if callable(getattr(message, "__dict__", None)):
                    message = message.__dict__()
                else:
                    message = dict(message)
                self.logger.debug(f"<- {message}")
                if self.ws is None or self.ws.closed:
                    raise asyncio.CancelledError()
                await self.ws.send_json(message)
        except asyncio.CancelledError:
            self.logger.warning("Writer task stopped.")

    async def reader(self):
        try:
            async with aiohttp.ClientSession() as session:
                self.logger.info(f"Connecting to {self.ws_url}")
                async with session.ws_connect(self.ws_url) as ws:
                    self.running = True
                    self.ws = ws
                    self.writer_task = asyncio.ensure_future(self.writer())
                    self.trigger("connected")

                    message: aiohttp.WSMessage
                    async for message in ws:
                        try:
                            if message.type == aiohttp.WSMsgType.TEXT:
                                self.logger.debug(f"-> {message.data}")
                                try:
                                    d_msg = WsClient.decode_message(message)
                                    self._reader_queue.put_nowait(d_msg)
                                    self.trigger(f"msg:{d_msg.type_}", **d_msg.data)
                                except ValueError:
                                    self.logger.error(f"Invalid incoming message: {message.data}")
                            elif message.type == aiohttp.WSMsgType.ERROR:
                                self.logger.error("Connection error")
                                break
                        except Exception as e:
                            self.logger.error("Unhandled exception in reader task!")
                            self.logger.error(f"{e}\n{traceback.format_exc()}")
        except asyncio.CancelledError:
            self.logger.warning("run task cancelled")
        finally:
            if self.writer_task is not None:
                self.writer_task.cancel()
            if self.ws is not None and not self.ws.closed:
                self.logger.info("Closing connection")
                try:
                    await self.ws.close()
                except Exception as e:
                    self.logger.error(f"Error while closing connection: {str(e)}")
            self.running = False
            self.trigger("disconnected")
            self.logger.info("Disconnected.")

    async def start(self) -> None:
        if self.running:
            raise RuntimeError("Client already running")
        self.reader_task = asyncio.ensure_future(self.reader())
        r = await self.wait("connected", "disconnected")
        if "disconnected" in r:
            raise RuntimeError("Cannot connect.")

    def stop(self):
        self.reader_task.cancel()

    def trigger(self, k_: str, **kwargs) -> None:
        k_ = k_.lower()
        for handler in self._event_handlers[k_]:
            asyncio.ensure_future(handler(**kwargs))
        e = self._events[k_]
        e.set()
        e.clear()

    async def _wait_for(self, event: str) -> str:
        await self._events[event.lower()].wait()
        return event

    async def wait(self, *events, return_when=asyncio.FIRST_COMPLETED) -> Optional[List[str]]:
        if not events:
            return
        done, pending = await asyncio.wait(
            [self._wait_for(event) for event in events],
            return_when=return_when
        )
        self.logger.debug(f"Got something (done:{done}, pending:{pending})")

        # Get the result(s) of the completed task(s).
        ret = [future.result() for future in done]

        # Cancel any events that didn't come in.
        for future in pending:
            future.cancel()
        return ret

    def on(self, event: str, f: Callable = None) -> Callable:
        if f is None:
            return functools.partial(self.on, event)  # type: ignore
        wrapped = f
        if not asyncio.iscoroutinefunction(wrapped):
            wrapped = asyncio.coroutine(wrapped)
        self._event_handlers[event.lower()].append(wrapped)
        return f
