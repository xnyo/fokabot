import logging
from typing import Callable, Dict, Any

from singletons.bot import Bot

bot = Bot()
logger = logging.getLogger("tournament")


def init():
    # Import sub plugins
    import plugins.tournament.beatmaps
    import plugins.tournament.create
    import plugins.tournament.join_leave
    import plugins.tournament.rolls


def resolve_match_update(f: Callable) -> Callable:
    async def wrapper(match: Dict[str, Any], **kwargs):
        if match["id"] not in bot.tournament_matches.keys():
            return
        return await f(match=match, tournament_match=bot.tournament_matches[match["id"]], **kwargs)
    return wrapper


def resolve_event(f: Callable) -> Callable:
    async def wrapper(match_id: int, **kwargs):
        if match_id not in bot.tournament_matches.keys():
            return
        return await f(match=bot.tournament_matches[match_id], **kwargs)
    return wrapper


def tournament_regex_pre(*, recipient: Dict[str, Any], pm: bool, **_) -> bool:
    """
    Regex pre that returns True only if the message is sent in a
    registered tournament match chat channel.

    :return: True if the message is sent in a tournament match chat channel
    """
    return \
        not pm and recipient["name"].startswith("#multi_") \
        and int(recipient["name"].split("_")[1]) in bot.tournament_matches.keys()
