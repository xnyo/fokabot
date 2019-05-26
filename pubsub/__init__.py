import json

import logging
from typing import Any, Union, Callable

from aioredis import Channel
from schema import Schema, And, Use, SchemaError

# from utils import raven
import singletons.bot


async def reader(channel: Channel):
    """
    Process incoming pubsub messages

    :param channel: aioredis Channel, must be a pattern channel
    :return:
    """
    # @raven.capture
    async def on_message():
        """
        Processes an incoming message, encapsulated in
        raven.capture to handle errors correctly

        :return:
        """
        # Get channel name and message
        channel_name, message = await channel.get(encoding="utf-8")
        logging.getLogger("pubsub").debug(f"{message} -> {channel_name}")
        channel_name = channel_name.decode()

        # Check if we are able to handle this channel
        if channel_name in singletons.bot.Bot().pubsub_binding_manager:
            # Await/run the handler function/coroutine
            await singletons.bot.Bot().pubsub_binding_manager[channel_name](message)
        else:   # pragma: no cover
            # Unregistered channel, do nothing
            logging.getLogger("pubsub").warning(
                f"Got pubsub message for unregistered channel ({message} -> {channel_name})"
            )

    # Accept only pattern channels
    if not channel.is_pattern:  # pragma: no cover
        raise TypeError("`channel` must be a pattern channel")

    # Await a message (blocks)
    while await channel.wait_message():
        # on_message is decorated by raven.capture, so we don't break the loop in case of an exception
        await on_message()


def schema(schema_: Union[Schema, dict]) -> Callable:
    def decorator(f: Callable):
        async def wrapper(data: str, *args, **kwargs) -> Any:
            s = Schema(And(Use(json.loads), schema_)) if type(schema_) is dict else schema_
            try:
                data = s.validate(data)
            except SchemaError as e:    # pragma: no cover
                logging.getLogger("schema").warning(f"Incoming data ({data}) doesn't satisfy schema ({e})")
                return
            return await f(data, *args, **kwargs)
        return wrapper
    return decorator
