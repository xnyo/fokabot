from typing import Optional, Dict, Any, Callable, Tuple

import asyncio

import logging
from schema import Schema, Use, And

import plugins.base
import utils
from constants.mods import Mod, ModSpecialMode
from constants.teams import Team
from plugins.base import Arg
from constants.privileges import Privileges
from singletons.bot import Bot
from utils import general, schema
from utils.rippleapi import BanchoApiBeatmap

bot = Bot()


def resolve_mp(f: Callable) -> Callable:
    async def wrapper(*, recipient: Dict[str, Any], **kwargs):
        assert recipient["display_name"] == "#multiplayer"
        match_id = int(recipient["name"].split("_")[1])
        return await f(match_id=match_id, recipient=recipient, **kwargs)
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


@bot.command("mp start")
@plugins.base.protected(Privileges.USER_TOURNAMENT_STAFF)
@plugins.base.multiplayer_only
@resolve_mp
@plugins.base.arguments(
    Arg("seconds", And(Use(int), lambda x: x >= 0), default=0, optional=True),
    Arg("force", And(str, Use(lambda x: x == "force")), default=False, optional=True)
)
async def start(match_id: int, seconds: int, recipient: Dict[str, Any], force: bool) -> str:
    async def start_after(timer_seconds: int):
        try:
            logging.debug("Start after task started")
            while timer_seconds > 0:
                if timer_seconds % 10 == 0 or timer_seconds < 10:
                    bot.send_message(f"Match starts in {timer_seconds} seconds.", recipient["name"])
                await asyncio.sleep(1)
                timer_seconds -= 1
            logging.debug("Starting")
            try:
                await bot.bancho_api_client.start_match(match_id, force=force)
            except utils.rippleapi.RippleApiResponseError as e:
                if e.data.get("code", None) == 409:
                    bot.send_message(
                        "Cannot start the match. There may be not enough players ready, invalid teams or the match"
                        "may already be in progress. Use '!mp start x force' to start the match anyways.",
                        recipient["name"]
                    )
                else:
                    bot.send_message(e.data.get("message", "Unknown API error"), recipient["name"])
            else:
                bot.send_message("Match started!", recipient["name"])
        except asyncio.CancelledError:
            bot.send_message("Match timer start cancelled!", recipient["name"])
        finally:
            # wtf pycharm
            bot.match_delayed_start_tasks.pop(match_id, None)
    if match_id in bot.match_delayed_start_tasks:
        return "This match is starting soon."
    logging.debug(f"Seconds: {seconds}")
    bot.match_delayed_start_tasks[match_id] = asyncio.ensure_future(start_after(seconds))
    if seconds > 0:
        # TODO: lock match for real
        return f"Match starts in {seconds} seconds. The match has been locked. " \
            f"Please don't leave the match during the " \
            f"countdown or you might receive a penality."


@bot.command("mp abort")
@plugins.base.protected(Privileges.USER_TOURNAMENT_STAFF)
@plugins.base.multiplayer_only
@resolve_mp
@plugins.base.base
async def abort(match_id: int) -> str:
    had_timer = True
    try:
        bot.match_delayed_start_tasks.pop(match_id).cancel()
    except KeyError:
        had_timer = False

    try:
        await bot.bancho_api_client.abort_match(match_id)
        return "Match aborted!"
    except utils.rippleapi.RippleApiResponseError as e:
        # 409 = match not in progress
        # and it is prefectly acceptable if we had a timer
        # (match not started yet)
        if e.data.get("code", None) != 409 or not had_timer:
            raise e


@bot.command("mp invite")
@plugins.base.protected(Privileges.USER_TOURNAMENT_STAFF)
@plugins.base.multiplayer_only
@resolve_mp
@plugins.base.arguments(
    Arg("username", Schema(str))
)
async def invite(match_id: int, username: str) -> str:
    user_id = await plugins.base.utils.username_to_user_id(username)
    await bot.bancho_api_client.invite(match_id, user_id)
    return f"{username} has been invited to this match"


@bot.command("mp kick")
@plugins.base.protected(Privileges.USER_TOURNAMENT_STAFF)
@plugins.base.multiplayer_only
@resolve_mp
@plugins.base.arguments(
    Arg("username", Schema(str))
)
async def kick(match_id: int, username: str) -> str:
    api_identifier = await plugins.base.utils.username_to_client_multiplayer(username, match_id)
    await bot.bancho_api_client.match_kick(match_id, api_identifier)
    return f"{username} has been kicked from this match"


@bot.command("mp map")
@plugins.base.protected(Privileges.USER_TOURNAMENT_STAFF)
@plugins.base.multiplayer_only
@resolve_mp
@plugins.base.arguments(
    Arg("beatmap_id", And(Use(int)))
)
async def map_(match_id: int, beatmap_id: int) -> str:
    await bot.bancho_api_client.edit_match(match_id, beatmap=BanchoApiBeatmap(beatmap_id))
    return "The beatmap has been updated"


@bot.command("mp password")
@plugins.base.protected(Privileges.USER_TOURNAMENT_STAFF)
@plugins.base.multiplayer_only
@resolve_mp
@plugins.base.arguments(
    Arg("password", Schema(str), rest=True)
)
async def password(match_id: int, password: str) -> str:
    await bot.bancho_api_client.edit_match(match_id, password=password)
    return "The password has been changed."


@bot.command("mp removepassword")
@plugins.base.protected(Privileges.USER_TOURNAMENT_STAFF)
@plugins.base.multiplayer_only
@resolve_mp
@plugins.base.base
async def remove_password(match_id: int) -> str:
    await bot.bancho_api_client.edit_match(match_id, password="")
    return "The password has been removed."


@bot.command("mp randompassword")
@plugins.base.protected(Privileges.USER_TOURNAMENT_STAFF)
@plugins.base.multiplayer_only
@resolve_mp
@plugins.base.base
async def random_password(match_id: int, sender: Dict[str, Any]) -> str:
    passwd = general.random_secure_string(8)
    await bot.bancho_api_client.edit_match(match_id, password=passwd)
    bot.send_message(f"New generated password for match #{match_id}: {passwd}", sender["username"])
    return "A new password has been set."


@bot.command("mp mods")
@plugins.base.protected(Privileges.USER_TOURNAMENT_STAFF)
@plugins.base.multiplayer_only
@resolve_mp
@plugins.base.arguments(
    Arg(
        "mods",
        schema.ModStringMultipleAndSpecialMode,
        rest=True
    )
)
async def mods_(match_id: int, mods: Tuple[ModSpecialMode, Mod]) -> str:
    special_mode, mods = mods
    await bot.bancho_api_client.edit_match(match_id, mods=mods, free_mod=special_mode == ModSpecialMode.FREE_MODS)
    if mods == Mod.NO_MOD:
        # NO_MOD is empty string in Mod.__str__()
        mods = "NO MOD"
    return f"Mods set to {mods}, free mods = {special_mode == ModSpecialMode.FREE_MODS}"


@bot.command("mp team")
@plugins.base.protected(Privileges.USER_TOURNAMENT_STAFF)
@plugins.base.multiplayer_only
@resolve_mp
@plugins.base.arguments(
    Arg("username", Schema(str)),
    Arg("colour", And(Use(lambda x: Team[x.strip().upper()]), lambda x: x != Team.NEUTRAL))
)
async def team(match_id: int, username: str, colour: Team) -> str:
    assert colour != Team.NEUTRAL
    api_identifier = await plugins.base.utils.username_to_client_multiplayer(username, match_id)
    await bot.bancho_api_client.set_team(match_id, api_identifier, colour)
    return f"Teams updated."
