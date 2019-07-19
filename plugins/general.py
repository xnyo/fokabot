from typing import Optional, Dict, Any

import random

from schema import Use, And

import plugins
from constants.action import Action
from singletons.bot import Bot
from utils.rippleapi import BanchoClientType

bot = Bot()


@bot.command("roll")
@plugins.arguments(plugins.Arg("number", And(Use(int), lambda x: x > 0), default=100, optional=True))
async def roll(username: str, channel: str, number: int, *args, **kwargs) -> str:
    """
    !roll <number>

    :param username:
    :param channel:
    :param number: max number, must > 0. Default: 100
    :return: a random number between 0 and some other number
    """
    return f"{username} rolls {random.randrange(0, number)} points!"


@bot.command("help")
async def help_(username: str, channel: str, message: str, *args, **kwargs) -> str:
    """
    !help

    :return: an help message with a link to FokaBot's command list
    """
    return "Click (here)[https://ripple.moe/index.php?p=16&id=4] for FokaBot's full command list"


@bot.command("bloodcat")
async def bloodcat(username: str, channel: str, message: str, *args, **kwargs) -> Optional[str]:
    """
    !bloodcat

    :return: a link to download the currently played beatmap from bloodcat.
             Works only in #multiplayer and #spectator
    """
    is_multi = channel.startswith("#multi_")
    is_spect = channel.startswith("#spect_")
    if not is_multi and not is_spect:
        return
    temp_id = int(channel.split("_")[1])
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
    cheesegull_response = await bot.cheesegull_api_client.get_beatmap(beatmap_id)
    if cheesegull_response is None:
        return "Sorry, I don't know this beatmap :/"
    return \
        f"Download [https://bloodcat.com/osu/s/{cheesegull_response['ParentSetID']} " \
        f"{beatmap_name}] from Bloodcat"
