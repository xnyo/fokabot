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
@plugins.public_only
@plugins.arguments(plugins.Arg("on", And(str, Use(lambda x: x.lower() == "on")), default=True, optional=True))
@plugins.protected(Privileges.ADMIN_CHAT_MOD)
async def moderated(username: str, channel: str, on: int) -> str:
    await bot.bancho_api_client.moderated(channel, on)
    return f"This channel is {'now' if on else 'no longer'} in moderated mode"


@bot.command("kick")
@plugins.arguments(plugins.Arg("target_username", And(str)))
@plugins.protected(Privileges.ADMIN_CHAT_MOD)
@plugins.resolve_target_username_to_client()
async def kick(username: str, channel: str, api_identifier: str, target_username: str) -> str:
    try:
        await bot.bancho_api_client.kick(api_identifier)
        return f"{target_username} has been kicked from the server."
    except NotFoundError:
        return f"{target_username} is not connected to bancho right now."


@bot.command("rtx")
@plugins.arguments(
    plugins.Arg("target_username", And(str)),
    plugins.Arg("message", And(str), rest=True)
)
@plugins.protected(Privileges.ADMIN_CHAT_MOD)
@plugins.resolve_target_username_to_client()
async def kick(username: str, channel: str, api_identifier: str, message: str) -> str:
    try:
        await bot.bancho_api_client.rtx(api_identifier, message)
        return ":ok_hand:"
    except NotFoundError:
        return "No such user."


def set_allowed(new_api_allowed: int) -> Callable:
    def wrapper(f: Callable):
        @plugins.arguments(
            plugins.Arg("target_username", And(str))
        )
        @plugins.protected(Privileges.ADMIN_BAN_USERS)
        @plugins.resolve_target_username_to_user_id
        async def decorator(username: str, channel: str, target_username: str, target_user_id: int) -> str:
            await bot.ripple_api_client.set_allowed(target_user_id, new_api_allowed)
            return await f(username, channel, target_username, target_user_id=target_user_id)
        return decorator
    return wrapper


@bot.command("ban")
@set_allowed(0)
async def ban(username: str, channel: str, target_username: str, target_user_id: int) -> str:
    return f"({target_username})[https://ripple.moe/u/{target_user_id}] has been banned!"


@bot.command("unban")
@set_allowed(1)
async def unban(username: str, channel: str, target_username: str, target_user_id: int) -> str:
    return f"({target_username})[https://ripple.moe/u/{target_user_id}] has been unbanned!"


# TODO: There's no way to restrict someone from the API afaik.
#  Ask howl if I can implement set_allowed with privileges=2 for restricted
@bot.command("restrict")
@set_allowed(2)
async def restrict(username: str, channel: str, target_username: str, target_user_id: int) -> str:
    return f"({target_username})[https://ripple.moe/u/{target_user_id}] has been restricted!"


@bot.command("silence")
@plugins.arguments(
    plugins.Arg("target_username", Schema(str)),
    plugins.Arg("how_many", Schema(Use(int))),
    plugins.Arg("unit", And(str, Use(SilenceUnit), error="Unit must be s/m/h/d"), example="s/m/h/d"),
    plugins.Arg("reason", Schema(str), rest=True),
)
@plugins.protected(Privileges.ADMIN_CHAT_MOD)
@plugins.resolve_target_username_to_user_id
async def silence(
    username: str, channel: str, target_username: str,
    target_user_id: int, how_many: int, unit: SilenceUnit,
    reason: str
) -> str:
    time_in_seconds = how_many * unit.seconds
    await bot.ripple_api_client.edit_user(
        target_user_id,
        silence_end=datetime.datetime.utcnow() + datetime.timedelta(seconds=time_in_seconds),
        silence_reason=reason
    )
    return f"{target_username} has been silenced for {time_in_seconds} seconds for the following reason: '{reason}'"


@bot.command("removesilence")
@plugins.arguments(
    plugins.Arg("target_username", Schema(str))
)
@plugins.protected(Privileges.ADMIN_CHAT_MOD)
@plugins.resolve_target_username_to_user_id
async def remove_silence(username: str, channel: str, target_username: str, target_user_id: int) -> str:
    await bot.ripple_api_client.edit_user(target_user_id, silence_end=datetime.date(1970, 1, 1))
    return f"{target_username}'s silence removed"
