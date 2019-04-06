from schema import Schema

from plugins import base, arguments, Arg, resolve_username_to_client
from singletons.bot import Bot

bot = Bot()


@bot.command("alert")
@base
@arguments(Arg("message", Schema(str), rest=True))
async def alert(username: str, channel: str, message: str) -> None:
    await bot.bancho_api_client.mass_alert(message)


@bot.command("alertuser")
@base
@arguments(
    Arg("target_username", Schema(str)),
    Arg("message", Schema(str), rest=True)
)
@resolve_username_to_client()
async def alert(username: str, channel: str, api_identifier: str, message: str, **kwargs) -> None:
    await bot.bancho_api_client.alert(api_identifier, message)
