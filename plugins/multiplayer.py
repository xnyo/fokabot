from typing import Optional

from schema import Schema, Use

import plugins
from constants.privileges import Privileges
from singletons.bot import Bot
from utils.rippleapi import BanchoApiBeatmap

bot = Bot()


@bot.command("mp make")
@plugins.arguments(
    plugins.Arg("name", Schema(str)),
    plugins.Arg("password", Schema(str), default=None, optional=True),
)
@plugins.protected(Privileges.USER_TOURNAMENT_STAFF)
async def make(username: str, channel: str, name: str, password: Optional[str]) -> str:
    match_id = await bot.bancho_api_client.create_match(
        name,
        password,
        beatmap=BanchoApiBeatmap(0, "a" * 32, "No song")
    )
    return f"Multiplayer match #{match_id} created!"


@bot.command("mp join")
@plugins.arguments(
    plugins.Arg("match_id", Use(int)),
    plugins.Arg("password", Schema(str), default=None, optional=True),
)
@plugins.protected(Privileges.USER_TOURNAMENT_STAFF)
@plugins.resolve_user_to_client()
async def join(username: str, channel: str, match_id: int, password: str, api_identifier: str) -> None:
    await bot.bancho_api_client.join_match(api_identifier, match_id, password)
