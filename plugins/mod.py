from schema import And, Use

import plugins
from constants.privileges import Privileges
from singletons.bot import Bot
from utils.rippleapi import NotFoundError

bot = Bot()


@bot.command("moderated")
@plugins.base
@plugins.arguments(plugins.Arg("on", And(str, Use(lambda x: x.lower() == "on")), default=True, optional=True))
@plugins.protected(Privileges.ADMIN_CHAT_MOD)
async def moderated(username: str, channel: str, on: int) -> str:
    await bot.bancho_api_client.moderated(channel, on)
    return f"This channel is {'now' if on else 'no longer'} in moderated mode"


@bot.command("kick")
@plugins.base
@plugins.arguments(plugins.Arg("target_username", And(str)))
@plugins.protected(Privileges.ADMIN_CHAT_MOD)
@plugins.resolve_username_to_client()
async def kick(username: str, channel: str, api_identifier: str, target_username: str) -> str:
    try:
        await bot.bancho_api_client.kick(api_identifier)
        return f"{target_username} has been kicked from the server."
    except NotFoundError:
        return f"{target_username} is not connected to bancho right now."


@bot.command("rtx")
@plugins.base
@plugins.arguments(
    plugins.Arg("target_username", And(str)),
    plugins.Arg("message", And(str), rest=True)
)
@plugins.protected(Privileges.ADMIN_CHAT_MOD)
@plugins.resolve_username_to_client()
async def kick(username: str, channel: str, api_identifier: str, message: str, **kwargs) -> str:
    try:
        await bot.bancho_api_client.rtx(api_identifier, message)
        return ":ok_hand:"
    except NotFoundError:
        return "No such user."
