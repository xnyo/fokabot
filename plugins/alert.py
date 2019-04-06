from schema import Schema

from plugins import base, arguments, Arg
from singletons.bot import Bot
from utils.rippleapi import RippleApiError

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
async def alert(username: str, channel: str, target_username: str, message: str) -> str:
    user_id = await bot.ripple_api_client.what_id(target_username)
    if user_id is None:
        return "No such user."
    client = await bot.bancho_api_client.get_client(user_id, game_only=True)
    if client is None:
        return "This user is not connected right now"
    await bot.bancho_api_client.alert(client["api_identifier"], message)
