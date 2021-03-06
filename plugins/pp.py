try:
    import ujson as json
except ImportError:
    import json
from typing import Optional, Callable, Any, Union, Dict

import re
from schema import And, Use

import plugins.base
from singletons.bot import Bot
from constants.game_modes import GameMode
from constants.mods import Mod
from utils import schema
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
    r"( ~Relax~)?"
    r"\x01$"
)


async def save_np_info(sender: Dict[str, Any], info: NpInfo, *, expire: int = 180) -> None:
    """
    Save np cache info in redis

    :param sender: sender dict coming from ws
    :param info: np info to save. It will be json-serialized.
    :param expire: redis key expire. Defaults to 180.
    :return:
    """
    with await bot.redis as conn:
        await conn.set(f"fokabot:np:{sender['api_identifier']}", json.dumps(info.jsonify()), expire=expire)


def resolve_np_info(f: Callable) -> Callable:
    """
    Decorator that passes bot.np_storage[api_identifier] to the
    np_info kwarg of the decorated function. If the api_identifier
    is not in the storage, an error message is returned instead.
    This will also save the new np info in redis after running
    the handler, so you can safely edit it inside the handler
    and expect it to be copied back to redis.

    :param f:
    :return:
    """
    async def wrapper(*, sender: Dict[str, Any], **kwargs) -> Any:
        redis_key = f"fokabot:np:{sender['api_identifier']}"
        try:
            with await bot.redis as conn:
                np_data = await conn.get(redis_key)
            if np_data is None:
                raise KeyError()
            json_data = json.loads(np_data.decode())
            if "beatmap_id" not in json_data:
                with await bot.redis as conn:
                    await conn.delete(redis_key)
                raise KeyError()
        except KeyError:
            return "Please send me a song with /np first."
        np_info = NpInfo(**json_data)
        r = await f(np_info=np_info, sender=sender, **kwargs)
        await save_np_info(sender, np_info)
        return r
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
    async def wrapper(*, np_info: Optional[NpInfo] = None, **kwargs) -> Any:
        r = await f(np_info=np_info, **kwargs)
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


async def last_inner(username: str, pm: bool) -> str:
    recent_scores = await bot.ripple_api_client.recent_scores(username=username)
    if not recent_scores:
        return "You have no scores :("
    score = recent_scores[0]
    msg = f"{username} | " if not pm else ""
    msg += f"[http://osu.ppy.sh/b/{score['beatmap']['beatmap_id']} {score['beatmap']['song_name']}]"
    msg += f" <{str(GameMode(score['play_mode']))}>"
    if score['mods'] != 0:
        msg += f" +{str(Mod(score['mods']))}"
    msg += f" ({score['accuracy']:.2f}%, {score['rank']})"
    msg += " (FC)" if score["full_combo"] else f" | {score['max_combo']}x/{score['beatmap']['max_combo']}x"
    msg += f" | {score['pp']:.2f}pp"
    msg += f" | {next((x for _, x in score['beatmap']['difficulty2'].items() if x > 0), 0):.2f}★"
    return msg


@bot.command("last")
@plugins.base.base
async def last(sender: Dict[str, Any], pm: bool) -> str:
    """
    !last
    Returns some information about the most recent score submitted by the user.

    :return:
    """
    return await last_inner(sender["username"], pm)


@bot.command(
    ("is playing", "is listening to", "is watching"),
    action=True
)
@plugins.base.private_only
@np_info_response
async def np(sender: Dict[str, Any], message: str, **_) -> Union[NpInfo, str, None]:
    """
    /np
    Returns PP information about the map provided by the user. PM only.

    :return:
    """
    match = NP_REGEX.fullmatch(message)
    if not match:
        # TODO: Sentry
        bot.logger.warning(f"/np message did not match regex: {message}")
        return
    id_type, id_, beatmap_name, game_mode, mods_str, relax_str = match.groups()
    if id_type == "s":
        # ?? Seems to be just a weird thing for old maps
        return "The map is too old"

    game_mode = GameMode.np_factory(game_mode)
    mods = Mod.np_factory(mods_str)
    if relax_str is not None:
        mods |= Mod.RELAX
    np_info = NpInfo(id_, game_mode, mods)
    await save_np_info(sender, np_info)
    return np_info


@bot.command("with")
@plugins.base.private_only
@plugins.base.arguments(
    plugins.base.Arg("mods", schema.ModStringSingle),
    intersect_kwargs=False
)
@resolve_np_info
@np_info_response
async def with_(mods: Mod, np_info: NpInfo, **_) -> None:
    """
    !with mods
    Returns PP information about the most recent map sent by this user to the bot with /np
    "mods" is a combination of short mod acronyms, such as "HDHR", "HDDT", "NF", ...

    :return:
    """
    np_info.mods = mods


@bot.command("acc")
@plugins.base.private_only
@plugins.base.arguments(
    plugins.base.Arg("accuracy", And(str, Use(float), Use(lambda x: round(x, 2)), lambda x: 0 < x <= 100)),
    intersect_kwargs=False
)
@resolve_np_info
@np_info_response
async def acc(accuracy: float, np_info: NpInfo, **_) -> None:
    """
    !acc accuracy
    Returns PP information about the most recent map sent by this user to the bot with /np
    "accuracy" is the input accuracy, 0 < accuracy <= 100

    :return:
    """
    if accuracy in (100, 99, 98, 95):
        # Use pre-computed acc values from db
        np_info.accuracy = None
    else:
        np_info.accuracy = accuracy


@bot.command("mode")
@plugins.base.private_only
@plugins.base.arguments(
    plugins.base.Arg("game_mode", schema.GameModeString),
    intersect_kwargs=False
)
@resolve_np_info
@np_info_response
async def mode(game_mode: GameMode, np_info: NpInfo, **_) -> None:
    """
    !mode game_mode
    Returns PP information about the most recent map sent by this user to the bot with /np
    "game_mode" is the game mode overwrite (std/taiko/ctb/mania)

    :return:
    """
    np_info.game_mode = game_mode
