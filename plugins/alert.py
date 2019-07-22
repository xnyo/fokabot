from schema import Schema

import plugins
import plugins.base
import plugins.base.utils
from constants.privileges import Privileges
from singletons.bot import Bot

bot = Bot()


@bot.command("alert")
@plugins.base.protected(Privileges.ADMIN_SEND_ALERTS)
@plugins.base.arguments(plugins.base.Arg("the_message", Schema(str), rest=True))
async def alert(the_message: str) -> None:
    await bot.bancho_api_client.mass_alert(the_message)


@bot.command("alertuser")
@plugins.base.protected(Privileges.ADMIN_SEND_ALERTS)
@plugins.base.arguments(
    plugins.base.Arg("username", Schema(str)),
    plugins.base.Arg("the_message", Schema(str), rest=True)
)
async def alert(username: str, the_message: str) -> None:
    api_identifier = await plugins.base.utils.username_to_client(username)
    await bot.bancho_api_client.alert(api_identifier, the_message)
