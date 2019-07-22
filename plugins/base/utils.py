import inspect
from typing import Callable, Dict, Any

from plugins import GenericBotError
from singletons.bot import Bot


async def username_to_client(username: str, game: bool = False) -> str:
    user_id = await Bot().ripple_api_client.what_id(username)
    if user_id is None:
        raise GenericBotError("No such user.")
    client = await Bot().bancho_api_client.get_client(user_id, game_only=game)
    if client is None:
        raise GenericBotError("This user is not connected right now")
    return client["api_identifier"]


async def username_to_user_id(username: str) -> int:
    user_id = await Bot().ripple_api_client.what_id(username)
    if user_id is None:
        raise GenericBotError(f"No such user ({username})")
    return user_id


def required_kwargs_only(f: Callable, all_kwargs: Dict[str, Any]) -> Dict[str, Any]:
    f_kwargs_keys = {k for k in inspect.signature(f).parameters.keys()}
    return {k: v for k, v in all_kwargs.items() if k in f_kwargs_keys & all_kwargs.keys()}