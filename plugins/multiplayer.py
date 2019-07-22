from typing import Optional, Dict, Any, Callable

from schema import Schema, Use, And

import plugins.base
from plugins.base import Arg
from constants.privileges import Privileges
from singletons.bot import Bot
from utils.rippleapi import BanchoApiBeatmap

bot = Bot()


def resolve_mp(f: Callable) -> Callable:
    async def wrapper(*, recipient: Dict[str, Any], **kwargs):
        assert recipient["display_name"] == "#multiplayer"
        match_id = int(recipient["name"].split("_")[1])
        return await f(match_id=match_id, **kwargs)
    return wrapper


@bot.command("mp make")
@plugins.base.protected(Privileges.USER_TOURNAMENT_STAFF)
@plugins.base.arguments(
    plugins.base.Arg("name", Schema(str)),
    plugins.base.Arg("password", Schema(str), default=None, optional=True),
)
async def make(name: str, password: Optional[str]) -> str:
    match_id = await bot.bancho_api_client.create_match(
        name,
        password,
        beatmap=BanchoApiBeatmap(0, "a" * 32, "No song")
    )
    return f"Multiplayer match #{match_id} created!"


@bot.command("mp join")
@plugins.base.protected(Privileges.USER_TOURNAMENT_STAFF)
@plugins.base.arguments(
    plugins.base.Arg("match_id", Use(int))
)
async def join(sender: Dict[str, Any], match_id: int) -> str:
    await bot.bancho_api_client.join_match(sender["api_identifier"], match_id)
    return f"Making {sender['api_identifier']} join match #{match_id}"


@bot.command("mp close")
@plugins.base.protected(Privileges.USER_TOURNAMENT_STAFF)
@plugins.base.multiplayer_only
@resolve_mp
@plugins.base.base
async def close(match_id: int) -> None:
    await bot.bancho_api_client.delete_match(match_id)


@bot.command("mp size")
@plugins.base.protected(Privileges.USER_TOURNAMENT_STAFF)
@plugins.base.multiplayer_only
@resolve_mp
@plugins.base.arguments(
    Arg("slots", And(Use(int), lambda x: 2 <= x <= 16, error="The slots number must be between 2 and 16 (inclusive)"))
)
async def size(match_id: int, slots: int) -> str:
    await bot.bancho_api_client.lock(match_id, slots=[{"id": x, "locked": x > slots - 1} for x in range(16)])
    return "Match size changed"


@bot.command("mp move")
@plugins.base.protected(Privileges.USER_TOURNAMENT_STAFF)
@plugins.base.multiplayer_only
@resolve_mp
@plugins.base.arguments(
    Arg("username", Schema(str)),
    Arg("slot", And(Use(int), lambda x: 0 <= x < 16, error="The slots number must be between 2 and 16 (inclusive)"))
)
async def move(username: str, slot: int, match_id: int) -> str:
    api_identifier = await plugins.base.utils.username_to_client_multiplayer(username, match_id)
    await bot.bancho_api_client.match_move_user(match_id, api_identifier, slot)
    return f"{username} moved to slot #{slot}"


@bot.command("mp host")
@plugins.base.protected(Privileges.USER_TOURNAMENT_STAFF)
@plugins.base.multiplayer_only
@resolve_mp
@plugins.base.arguments(
    Arg("username", Schema(str))
)
async def move(username: str, match_id: int) -> str:
    api_identifier = await plugins.base.utils.username_to_client_multiplayer(username, match_id)
    await bot.bancho_api_client.transfer_host(match_id, api_identifier)
    return f"{username} is now the host of this match."


@bot.command("mp clearhost")
@plugins.base.protected(Privileges.USER_TOURNAMENT_STAFF)
@plugins.base.multiplayer_only
@resolve_mp
@plugins.base.base
async def clear_host(match_id: int) -> str:
    await bot.bancho_api_client.clear_host(match_id)
    return f"Host removed."
