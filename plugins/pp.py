import plugins
from singletons.bot import Bot
from constants.game_modes import GameMode
from constants.mods import Mod

bot = Bot()


@bot.command("last")
@plugins.base
async def last(username: str, channel: str, *args, **kwargs) -> str:
    print(args)
    print(kwargs)
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
