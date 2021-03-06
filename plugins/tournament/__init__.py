import logging
from typing import Callable, Dict, Any

from constants.tournament_state import TournamentState
from singletons.bot import Bot
from utils import misirlou

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


def resolve(f: Callable) -> Callable:
    async def wrapper(*, recipient: Dict[str, Any], **kwargs):
        assert recipient["display_name"] == "#multiplayer"
        match_id = int(recipient["name"].split("_")[1])
        if match_id not in bot.tournament_matches.keys():
            return
        return await f(match=bot.tournament_matches[match_id], recipient=recipient, **kwargs)
    return wrapper


def cap_or_team_members_only(f: Callable) -> Callable:
    async def wrapper(*, sender: Dict[str, Any], match: misirlou.Match, **kwargs):
        uid = sender["user_id"]
        team = match.get_user_team(uid)
        if team is None:
            # Non-player (ref?) tried to trigger a player-only command, fail silently
            return
        if team.captain_in_match and uid != team.captain:
            # Captain is in match, abort!
            return f"{sender['username']}, only the captain of your team can use this command."
        # Captain not in match, allow it
        return await f(match=match, sender=sender, **kwargs)
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


def state(s: TournamentState) -> Callable:
    def decorator(f: Callable) -> Callable:
        async def wrapper(match: misirlou.Match, **kwargs) -> Any:
            if match.state != s:
                # Wrong state!
                return
            return await f(match=match, **kwargs)
        return wrapper
    return decorator
