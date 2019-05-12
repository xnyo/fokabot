from functools import reduce
from typing import Optional

import re

import plugins
from singletons.bot import Bot
from constants.game_modes import GameMode
from constants.mods import Mod
from utils import general
from utils.letsapi import LetsApiError

bot = Bot()
NP_REGEX = re.compile(
    r"^\x01ACTION is "
    r"(?:(?:playing)|(?:listening to)|(?:watching)) "
    r"\[https://osu\.ppy\.sh/(b|s)/(\d+) (.+)\]"
    r"(?: <(.+)>)"
    r"?((?: (?:\+|\-)\w+)*)"
    r"(?: \|\w+\|)?"
    r"\x01$"
)
MODS_MAPPING = {
    "Easy": Mod.EASY,
    "NoFail": Mod.NO_FAIL,
    "Hidden": Mod.HIDDEN,
    "HardRock": Mod.HARD_ROCK,
    "Nightcore": Mod.DOUBLE_TIME,
    "DoubleTime": Mod.DOUBLE_TIME,
    "HalfTime": Mod.HALF_TIME,
    "Flashlight": Mod.FLASHLIGHT,
    "SpunOut": Mod.SPUN_OUT
}
GAME_MODES_MAPPING = {
    "CatchTheBeat": GameMode.CATCH_THE_BEAT,
    "Taiko": GameMode.TAIKO,
    "osu!mania": GameMode.MANIA
}


@bot.command("last")
@plugins.base
async def last(username: str, channel: str, *args, **kwargs) -> str:
    recent_scores = await bot.ripple_api_client.recent_scores(username=username)
    if not recent_scores:
        return "You have no scores :("
    score = recent_scores[0]
    msg = f"{username} | " if channel.startswith("#") else ""
    msg += f"[http://osu.ppy.sh/b/{score['beatmap']['beatmap_id']} {score['beatmap']['song_name']}]"
    msg += f" <{GameMode(score['play_mode']).for_db()}>"
    if score['mods'] != 0:
        msg += f" +{Mod(score['mods']).readable()}"
    msg += f" ({score['accuracy']:.2f}%, {score['rank']})"
    msg += " (FC)" if score["full_combo"] else f" | {score['max_combo']}x/{score['beatmap']['max_combo']}x"
    msg += f" | {score['pp']:.2f}pp"
    msg += f" | {next((x for _, x in score['beatmap']['difficulty2'].items() if x > 0), 0):.2f}★"
    return msg


@bot.command(
    ("is playing", "is listening to", "is watching"),
    action=True
)
@plugins.base
@plugins.private_only
async def np(username: str, channel: str, message: str, *args, **kwargs) -> Optional[str]:
    match = NP_REGEX.fullmatch(message)
    if not match:
        # TODO: Sentry
        bot.logger.warning(f"/np message did not match regex: {message}")
        return
    id_type, id_, beatmap_name, game_mode, mods_str = match.groups()
    if id_type == "s":
        # ?? Seems to be just a weird thing for old maps
        return "The map is too old"
    if game_mode in GAME_MODES_MAPPING.keys():
        game_mode = GAME_MODES_MAPPING[game_mode]
    else:
        game_mode = GameMode.STANDARD
    mods = reduce(
        lambda x, y: x | y,
        (MODS_MAPPING.get(x.lstrip("+-"), Mod.NO_MOD) for x in mods_str.strip().split(" "))
    )
    try:
        return str(await bot.lets_api_client.get_pp(id_, game_mode, mods))
    except LetsApiError as e:
        return f"Error: {str(e)}"
