from singletons.bot import Bot
import plugins.base

bot = Bot()


@bot.client.on("tournament_first_rolled")
@plugins.base.wrap_response_multiplayer
async def tournament_first_rolled(match_id: int) -> str:
    match = bot.tournament_matches[match_id]
    other_team = match.team_a if match.team_a.roll is None else match.team_b
    return f"{match.captain_or_team_name(other_team)}, please roll."


@bot.client.on("tournament_both_rolled")
async def tournament_both_rolled(match_id: int) -> None:
    match = bot.tournament_matches[match_id]
    for msg in (
        f"{match.captain_or_team_name(match.roll_winner)} won the roll!",
        "Please pick your first ban. Here's the pool:"
    ):
        bot.send_message(msg, match.chat_channel_name)
    send_map_pool(match)
    send_ask_beatmap(match, match.roll_winner, operation="ban", confirmation=True)
