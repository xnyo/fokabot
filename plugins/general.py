from typing import Optional, Dict, Any

import random

from schema import Use, And

import plugins.base
import plugins.base.filters
from constants.action import Action
from singletons.bot import Bot
from utils.rippleapi import BanchoClientType
import utils.beatmaps

bot = Bot()


@bot.command("roll")
@plugins.base.arguments(plugins.base.Arg("number", And(Use(int), lambda x: x > 0), default=100, optional=True))
async def roll(sender: Dict[str, Any], number: int) -> str:
    """
    !roll <number>

    :param sender:
    :param number: max number, must > 0. Default: 100
    :return: a random number between 0 and some other number
    """
    return f"{sender['username']} rolls {random.randrange(0, number)} points!"


@bot.command("help")
@plugins.base.base
async def help_() -> str:
    """
    !help

    :return: an help message with a link to FokaBot's command list
    """
    return "Click (here)[https://ripple.moe/index.php?p=16&id=4] for FokaBot's full command list"


@bot.command(("bloodcat", "beatconnect", "mirror", "b"))
@plugins.base.trigger_filter_or(plugins.base.filters.is_spect, plugins.base.filters.is_multi)
@plugins.base.base
async def bloodcat(recipient: Dict[str, Any]) -> Optional[str]:
    """
    !bloodcat / !beatconnect / !mirror

    :return: a link to download the currently played beatmap from beatconnect and bloodcat.
             Works only in #multiplayer and #spectator
    """
    is_multi = recipient["display_name"] == "#multiplayer"
    is_spect = recipient["display_name"] == "#spectator"
    assert is_multi or is_spect
    temp_id = int(recipient["name"].split("_")[1])
    if is_multi:
        match_info = await bot.bancho_api_client.get_match_info(temp_id)
        if match_info.get("beatmap", None) is None:
            return
        beatmap_id = match_info["beatmap"]["id"]
        beatmap_name = match_info["beatmap"]["name"]
    else:
        clients = await bot.bancho_api_client.get_clients(temp_id)
        client = next(
            (
                x for x in clients
                if x["type"] == BanchoClientType.OSU
                and Action(x["action"]["id"]).playing
                and x["action"]["beatmap"] is not None
            ),
            None
        )
        if client is None:
            return "The spectator host is not playing right now."
        beatmap_id = client["action"]["beatmap"]["id"]
        beatmap_name = client["action"]["text"]
    assert beatmap_id is not None
    beatmap_set_id = await utils.beatmaps.get_beatmap_set_id(beatmap_id, non_cheesegull_only=False)
    if beatmap_set_id is None:
        return "Sorry, I don't know this beatmap :/"
    return await utils.beatmaps.get_download_message(beatmap_set_id, beatmap_name)
