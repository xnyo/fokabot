import re
import plugins.tournament
from singletons.bot import Bot
from utils import misirlou

bot = Bot()


def send_map_pool(match: misirlou.Match):
    """
    Sends multiple messages containing the map pool

    :param match: misirlou match
    """
    for k, group in match.tournament.pool.items():
        for i, beatmap in enumerate(group):
            bot.send_message(f"► {beatmap.mods.tournament_str}{i + 1}: {beatmap.name}", match.chat_channel_name)


def send_ask_beatmap(
    match: misirlou.Match, picking_team: misirlou.Team, operation: str, confirmation: bool
) -> None:
    who = match.captain_or_team_members(picking_team)
    if not picking_team.captain_in_match:
        who += ", any of you"
    bot.send_message(
        f"{who}, please type one beatmap you want to {operation} (eg: NM1, HD2, etc). "
        f"I will{' not ' if not confirmation else ' '}ask for confirmation.",
        match.chat_channel_name
    )


@bot.command(re.compile(r"(NM|HD|HR|DT|FM)+(\d)", re.IGNORECASE), pre=plugins.tournament.tournament_regex_pre)
async def on_map(**_) -> str:
    return "ok"
