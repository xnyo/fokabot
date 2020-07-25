from singletons.bot import Bot
import plugins.base
import plugins.tournament.beatmaps
from utils import misirlou

bot = Bot()


@bot.client.on("tournament_first_rolled")
@plugins.tournament.resolve_event
@plugins.base.wrap_response_multiplayer
async def tournament_first_rolled(match: misirlou.Match) -> str:
    other_team = match.team_a if match.team_a.roll is None else match.team_b
    return f"{match.captain_or_team_name(other_team)}, please roll."


@bot.client.on("tournament_both_rolled")
@plugins.tournament.resolve_event
async def tournament_both_rolled(match: misirlou.Match) -> None:
    for msg in (
        f"{match.captain_or_team_name(match.roll_winner)} won the roll!",
        "Please pick your first ban. Here's the pool:"
    ):
        bot.send_message(msg, match.chat_channel_name)
    plugins.tournament.beatmaps.send_map_pool(match)
    plugins.tournament.beatmaps.send_ask_beatmap(match, match.roll_winner, operation="ban", confirmation=True)
