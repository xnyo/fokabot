from schema import Schema

import plugins
from singletons.bot import Bot

bot = Bot()


@bot.command("alert")
@plugins.base
@plugins.arguments(plugins.Arg("message", Schema(str), rest=True))
async def alert(username: str, channel: str, message: str) -> None:
    await bot.bancho_api_client.mass_alert(message)


@bot.command("alertuser")
@plugins.base
@plugins.arguments(
    plugins.Arg("target_username", Schema(str)),
    plugins.Arg("message", Schema(str), rest=True)
)
@plugins.resolve_username_to_client()
async def alert(username: str, channel: str, api_identifier: str, message: str, **kwargs) -> None:
    await bot.bancho_api_client.alert(api_identifier, message)
