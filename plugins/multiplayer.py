from typing import Optional, Dict, Any

from schema import Schema, Use

import plugins
from constants.privileges import Privileges
from singletons.bot import Bot
from utils.rippleapi import BanchoApiBeatmap

bot = Bot()


@bot.command("mp make")
@plugins.protected(Privileges.USER_TOURNAMENT_STAFF)
@plugins.arguments(
    plugins.Arg("name", Schema(str)),
    plugins.Arg("password", Schema(str), default=None, optional=True),
)
async def make(name: str, password: Optional[str]) -> str:
    match_id = await bot.bancho_api_client.create_match(
        name,
        password,
        beatmap=BanchoApiBeatmap(0, "a" * 32, "No song")
    )
    return f"Multiplayer match #{match_id} created!"


@bot.command("mp join")
@plugins.protected(Privileges.USER_TOURNAMENT_STAFF)
@plugins.arguments(
    plugins.Arg("match_id", Use(int))
)
async def join(sender: Dict[str, Any], match_id: int) -> str:
    await bot.bancho_api_client.join_match(sender["api_identifier"], match_id)
    return f"Making {sender['api_identifier']} join match #{match_id}"
