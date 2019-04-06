from schema import And, Use

from plugins import arguments, Arg, base
from singletons.bot import Bot

bot = Bot()


@bot.command("moderated")
@base
@arguments(Arg("on", And(str, Use(lambda x: x.lower() == "on")), default=True))
async def moderated(username: str, channel: str, on: int) -> str:
    response = await bot.bancho_api_client.moderated(channel, on)
    return response.get("message", None)
