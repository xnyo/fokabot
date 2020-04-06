import inspect
from typing import Callable, Dict, Any, Optional

import plugins
import plugins.base
import singletons.bot
from utils.general import safefify_username


async def username_to_client(username: str, game: bool = False) -> str:
    user_id = await singletons.bot.Bot().ripple_api_client.what_id(username)
    if user_id is None:
        raise plugins.base.GenericBotError("No such user.")
    client = await singletons.bot.Bot().bancho_api_client.get_client(user_id, game_only=game)
    if client is None:
        raise plugins.base.GenericBotError("This user is not connected right now")
    return client["api_identifier"]


async def username_to_client_multiplayer(username: str, match_id: int) -> str:
    def username_filter(wanted_username: str, slot: Optional[Dict[str, Any]]) -> bool:
        if slot is None:
            return False
        user = slot.get("user", None)
        if user is None:
            return False
        return safefify_username(user.get("username")) == safefify_username(wanted_username)

    match_info = await singletons.bot.Bot().bancho_api_client.get_match_info(match_id)
    if match_info is None:
        raise plugins.base.GenericBotError("No such multiplayer match.")
    api_identifier = next(
        (
            slot["user"]["api_identifier"]
            for slot in match_info["slots"]
            if username_filter(username, slot)
        ), None
    )
    if api_identifier is None:
        raise plugins.base.GenericBotError("That user is not in this match")
    return api_identifier


async def username_to_user_id(username: str) -> int:
    user_id = await singletons.bot.Bot().ripple_api_client.what_id(username)
    if user_id is None:
        raise plugins.base.GenericBotError(f"No such user ({username})")
    return user_id


def required_kwargs_only(f: Callable, **all_kwargs) -> Dict[str, Any]:
    f_kwargs_keys = {k for k in inspect.signature(f).parameters.keys()}
    return {k: v for k, v in all_kwargs.items() if k in f_kwargs_keys & all_kwargs.keys()}
