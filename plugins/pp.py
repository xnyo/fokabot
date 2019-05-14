from typing import Optional, Callable, Any, Union

import re
from schema import And, Use

import plugins
from singletons.bot import Bot
from constants.game_modes import GameMode
from constants.mods import Mod
from utils.letsapi import LetsApiError
from utils.np_storage import NpInfo

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


def resolve_np_info(f: Callable) -> Callable:
    """
    Decorator that passes bot.np_storage[username] to the
    np_info kwarg of the decorated function. If there username
    is not in the storage, an error message is returned instead.

    :param f:
    :return:
    """
    async def wrapper(username: str, channel: str, *args, **kwargs) -> Any:
        try:
            np_info = bot.np_storage[username]
        except KeyError:
            return "Please send me a song with /np first."
        return await f(username, channel, *args, np_info=np_info, **kwargs)
    return wrapper


def np_info_response(f: Callable) -> Callable:
    """
    A decorator that returns a message containing pp information for
    a particular beatmap. The np info sent to the client is be determined
    by (in order of priority):
    1) If the value returned by the decorated function is a `NpInfo` object, it'll
       be used to make the LETS API call and the formatted response (with __str__)
       will be returned.
    2) The np_info kwarg, but only if the decorated function returns None.
    You can easily use the 2) by decorating this decorator with @resolve_np_info.
    If the decorated function returns something that's neither None nor an `NpInfo` object,
    the value returned by the decorated function is returned by this decorator too.
    This can be used to return any other message (eg: errors).

    :param f:
    :return:
    """
    async def wrapper(username: str, channel: str, *args, np_info: Optional[NpInfo] = None, **kwargs) -> Any:
        r = await f(username, channel, *args, np_info=np_info, **kwargs)
        if r is not None and type(r) is not NpInfo:
            return r
        np_info = next((x for x in (r, np_info) if type(x) is NpInfo), None)
        if np_info is not None:
            try:
                return str(
                    await bot.lets_api_client.get_pp(
                        np_info.beatmap_id,
                        np_info.game_mode,
                        np_info.mods,
                        np_info.accuracy
                    )
                )
            except LetsApiError as e:
                return f"Error: {str(e)}"
    return wrapper


@bot.command("last")
@plugins.base
async def last(username: str, channel: str, *args, **kwargs) -> str:
    """
    !last
    Returns some information about the most recent score submitted by the user.

    :param username:
    :param channel:
    :param args:
    :param kwargs:
    :return:
    """
    recent_scores = await bot.ripple_api_client.recent_scores(username=username)
    if not recent_scores:
        return "You have no scores :("
    score = recent_scores[0]
    msg = f"{username} | " if channel.startswith("#") else ""
    msg += f"[http://osu.ppy.sh/b/{score['beatmap']['beatmap_id']} {score['beatmap']['song_name']}]"
    msg += f" <{GameMode(score['play_mode']).for_db()}>"
    if score['mods'] != 0:
        msg += f" +{str(Mod(score['mods']))}"
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
@np_info_response
async def np(username: str, channel: str, message: str, *args, **kwargs) -> Union[NpInfo, str, None]:
    """
    /np
    Returns PP information about the map provided by the user. PM only.

    :param username:
    :param channel:
    :param message:
    :param args:
    :param kwargs:
    :return:
    """
    match = NP_REGEX.fullmatch(message)
    if not match:
        # TODO: Sentry
        bot.logger.warning(f"/np message did not match regex: {message}")
        return
    id_type, id_, beatmap_name, game_mode, mods_str = match.groups()
    if id_type == "s":
        # ?? Seems to be just a weird thing for old maps
        return "The map is too old"

    game_mode = GameMode.np_factory(game_mode)
    mods = Mod.np_factory(mods_str)
    bot.np_storage[username] = NpInfo(id_, game_mode, mods)
    return bot.np_storage[username]


@bot.command("with")
@plugins.base
@plugins.private_only
@plugins.arguments(plugins.Arg("mods", And(str, Use(Mod.short_factory))))
@resolve_np_info
@np_info_response
async def with_(username: str, channel: str, mods: Mod, *, np_info: NpInfo, **kwargs) -> None:
    """
    !with mods
    Returns PP information about the most recent map sent by this user to the bot with /np
    "mods" is a combination of short mod acronyms, such as "HDHR", "HDDT", "NF", ...

    :param username:
    :param channel:
    :param mods:
    :param np_info:
    :param kwargs:
    :return:
    """
    np_info.mods = mods
