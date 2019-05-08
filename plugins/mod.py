import datetime
from typing import Callable

from schema import And, Use, Schema

import plugins
from constants.privileges import Privileges
from constants.silence_units import SilenceUnit
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
async def kick(username: str, channel: str, api_identifier: str, message: str) -> str:
    try:
        await bot.bancho_api_client.rtx(api_identifier, message)
        return ":ok_hand:"
    except NotFoundError:
        return "No such user."


def set_allowed(new_api_allowed: int) -> Callable:
    def wrapper(f: Callable):
        @plugins.base
        @plugins.arguments(
            plugins.Arg("target_username", And(str))
        )
        @plugins.protected(Privileges.ADMIN_BAN_USERS)
        async def decorator(username: str, channel: str, target_username: str) -> str:
            # TODO: decorator
            user_id = await bot.ripple_api_client.what_id(target_username)
            if user_id is None:
                return f"No such user ({target_username})"
            await bot.ripple_api_client.set_allowed(user_id, new_api_allowed)
            return await f(username, channel, target_username, user_id=user_id)
        return decorator
    return wrapper


@bot.command("ban")
@set_allowed(0)
async def ban(username: str, channel: str, target_username: str, user_id: int) -> str:
    return f"({target_username})[https://ripple.moe/u/{user_id}] has been banned!"


@bot.command("unban")
@set_allowed(1)
async def unban(username: str, channel: str, target_username: str, user_id: int) -> str:
    return f"({target_username})[https://ripple.moe/u/{user_id}] has been unbanned!"


# TODO: There's no way to restrict someone from the API afaik.
#  Ask howl if I can implement set_allowed with privileges=2 for restricted
@bot.command("restrict")
@set_allowed(2)
async def restrict(username: str, channel: str, target_username: str, user_id: int) -> str:
    return f"({target_username})[https://ripple.moe/u/{user_id}] has been restricted!"


@bot.command("silence")
@plugins.base
@plugins.arguments(
    plugins.Arg("target_username", Schema(str)),
    plugins.Arg("how_many", Schema(Use(int))),
    plugins.Arg("unit", And(str, Use(SilenceUnit), error="Unit must be s/m/h/d")),
    plugins.Arg("reason", Schema(str), rest=True),
)
@plugins.protected(Privileges.ADMIN_CHAT_MOD)
async def silence(
    username: str, channel: str, target_username: str, how_many: int, unit: SilenceUnit, reason: str
) -> str:
    time_in_seconds = how_many * unit.seconds
    # TODO: decorator
    user_id = await bot.ripple_api_client.what_id(target_username)
    if user_id is None:
        return f"No such user ({target_username})"
    await bot.ripple_api_client.edit_user(
        user_id,
        silence_end=datetime.datetime.utcnow() + datetime.timedelta(seconds=time_in_seconds),
        silence_reason=reason
    )
