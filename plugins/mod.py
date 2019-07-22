import datetime
from typing import Callable, Dict, Any

from schema import And, Use, Schema

import plugins
import plugins.base.utils
from constants.privileges import Privileges
from constants.silence_units import SilenceUnit
from singletons.bot import Bot
from utils.rippleapi import NotFoundError

bot = Bot()


@bot.command("moderated")
@plugins.public_only
@plugins.protected(Privileges.ADMIN_CHAT_MOD)
@plugins.arguments(plugins.Arg("on", And(str, Use(lambda x: x.lower() == "on")), default=True, optional=True))
async def moderated(recipient: Dict[str, Any], on: int) -> str:
    await bot.bancho_api_client.moderated(recipient["name"], on)
    return f"This channel is {'now' if on else 'no longer'} in moderated mode"


@bot.command("kick")
@plugins.protected(Privileges.ADMIN_CHAT_MOD)
@plugins.arguments(plugins.Arg("username", And(str)))
async def kick(username: str) -> str:
    api_identifier = await plugins.base.utils.username_to_client(username)
    try:
        await bot.bancho_api_client.kick(api_identifier)
        return f"{username} has been kicked from the server."
    except NotFoundError:
        return f"{username} is not connected to bancho right now."


@bot.command("rtx")
@plugins.protected(Privileges.ADMIN_CHAT_MOD)
@plugins.arguments(
    plugins.Arg("username", And(str)),
    plugins.Arg("the_message", And(str), rest=True)
)
async def rtx(username: str, the_message: str) -> str:
    api_identifier = await plugins.base.utils.username_to_client(username)
    try:
        await bot.bancho_api_client.rtx(api_identifier, the_message)
        return ":ok_hand:"
    except NotFoundError:
        return "No such user."


def set_allowed(new_api_allowed: int) -> Callable:
    def wrapper(f: Callable):
        @plugins.protected(Privileges.ADMIN_BAN_USERS)
        @plugins.arguments(plugins.Arg("username", And(str)))
        async def decorator(*, username: str, **kwargs) -> str:
            target_user_id = await plugins.base.utils.username_to_user_id(username)
            await bot.ripple_api_client.set_allowed(target_user_id, new_api_allowed)
            return await f(**plugins.base.utils.required_kwargs_only(f, {"user_id": target_user_id, "username": username, **kwargs}))
        return decorator
    return wrapper


@bot.command("ban")
@set_allowed(0)
async def ban(username: str, user_id: int) -> str:
    return f"({username})[https://ripple.moe/u/{user_id}] has been banned!"


@bot.command("unban")
@set_allowed(1)
async def unban(username: str, user_id: int) -> str:
    return f"({username})[https://ripple.moe/u/{user_id}] has been unbanned!"


@bot.command("restrict")
@set_allowed(2)
async def restrict(username: str, user_id: int) -> str:
    return f"({username})[https://ripple.moe/u/{user_id}] has been restricted!"


@bot.command("silence")
@plugins.protected(Privileges.ADMIN_CHAT_MOD)
@plugins.arguments(
    plugins.Arg("username", Schema(str)),
    plugins.Arg("how_many", Schema(Use(int))),
    plugins.Arg("unit", And(str, Use(SilenceUnit), error="Unit must be s/m/h/d"), example="s/m/h/d"),
    plugins.Arg("reason", Schema(str), rest=True),
)
async def silence(username: str, how_many: int, unit: SilenceUnit, reason: str) -> str:
    user_id = await plugins.base.utils.username_to_user_id(username)
    time_in_seconds = how_many * unit.seconds
    await bot.ripple_api_client.edit_user(
        user_id,
        silence_end=datetime.datetime.utcnow() + datetime.timedelta(seconds=time_in_seconds),
        silence_reason=reason
    )
    return f"{username} has been silenced for {time_in_seconds} seconds for the following reason: '{reason}'"


@bot.command("removesilence")
@plugins.protected(Privileges.ADMIN_CHAT_MOD)
@plugins.arguments(
    plugins.Arg("username", Schema(str))
)
async def remove_silence(username: str) -> str:
    user_id = await plugins.base.utils.username_to_user_id(username)
    await bot.ripple_api_client.edit_user(user_id, silence_end=datetime.date(1970, 1, 1))
    return f"{username}'s silence removed"
