import re
from typing import Dict, Any, Optional

import plugins.tournament
import plugins.base
from singletons.bot import Bot
from utils import misirlou

bot = Bot()


class BanError(Exception):
    pass


def send_map_pool(match: misirlou.Match):
    """
    Sends multiple messages containing the map pool

    :param match: misirlou match
    """
    for k, group in match.tournament.pool.items():
        for i, beatmap in enumerate(group):
            if beatmap in match.bans:
                continue
            bot.send_message(f"► {beatmap.mods.tournament_str}{i + 1}: {beatmap.name}", match.chat_channel_name)


def send_ask_beatmap(match: misirlou.Match, operation: str, confirmation: bool) -> None:
    who = match.captain_or_team_members(match.picking_team)
    if not match.picking_team.captain_in_match:
        who += ", any of you"
    bot.send_message(
        f"{who}, please type one beatmap you want to {operation} (eg: NM1, HD2, etc). "
        f"I will{' not ' if not confirmation else ' '}ask for confirmation.",
        match.chat_channel_name
    )


def _ban_map(match: misirlou.Match, beatmap: misirlou.Beatmap) -> str:
    if match.picked_beatmap in match.bans:
        # Beatmap already banned, reset pick
        match.picked_beatmap = None
        raise BanError("This beatmap is already banned. Please choose another one.")
    match.bans.add(match.picked_beatmap)
    b_name = match.picked_beatmap.name
    # Reset pick and confirmation
    match.picked_beatmap = None
    match.needs_confirmation = True
    return f""""{b_name}" has been banned from this match."""


@bot.command(re.compile(r"(NM|HD|HR|DT|FM)+(\d+)", re.IGNORECASE), pre=plugins.tournament.tournament_regex_pre)
@plugins.tournament.resolve
@plugins.tournament.cap_or_team_members_only
@plugins.base.wrap_caller
async def on_map(sender: Dict[str, Any], match: misirlou.Match, parts, **_) -> str:
    # sender, recipient, pm, message, parts
    group, idx = parts[0], int(parts[1])
    beatmap = match.tournament.acronym_to_beatmap(group, idx)
    if beatmap is None:
        return "Invalid beatmap. Please type a valid one."
    if match.needs_confirmation:
        match.picked_beatmap = beatmap
        return f"""You want to ban "{beatmap.name}", correct? Please type 'yes' or 'no'."""
    # No confirmation fu
    try:
        return _ban_map(match, match.picked_beatmap)
    except BanError as e:
        return str(e)


@bot.command(re.compile(r"yes", re.IGNORECASE), pre=plugins.tournament.tournament_regex_pre)
@plugins.tournament.resolve
@plugins.tournament.cap_or_team_members_only
async def yes(sender: Dict[str, Any], match: misirlou.Match, parts, **_) -> Optional[str]:
    if match.picked_beatmap is None:
        # No beatmap picked yet
        return
    try:
        return _ban_map(match, match.picked_beatmap)
    except BanError as e:
        return str(e)


@bot.command(re.compile(r"no", re.IGNORECASE), pre=plugins.tournament.tournament_regex_pre)
@plugins.tournament.resolve
@plugins.tournament.cap_or_team_members_only
async def no(sender: Dict[str, Any], match: misirlou.Match, parts, **_) -> None:
    match.needs_confirmation = False
    bot.send_message("Ban cancelled.", match.chat_channel_name)
    send_ask_beatmap(match, "ban", confirmation=False)
