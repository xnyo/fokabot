from schema import And, Use

import plugins
from singletons.bot import Bot

bot = Bot()


@bot.command("moderated")
@plugins.base
@plugins.arguments(plugins.Arg("on", And(str, Use(lambda x: x.lower() == "on")), default=True))
async def moderated(username: str, channel: str, on: int) -> str:
    response = await bot.bancho_api_client.moderated(channel, on)
    return response.get("message", None)


@bot.command("kick")
@plugins.base
@plugins.arguments(plugins.Arg("target_username", And(str)))
@plugins.resolve_username_to_client()
async def kick(username: str, channel: str, api_identifier: str, target_username: str) -> str:
    success = await bot.bancho_api_client.kick(api_identifier)
    return f"{target_username} has been kicked from the server." if success else "The specified user is not connected."

