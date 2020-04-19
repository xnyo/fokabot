from typing import Tuple
import datetime

from schema import And, Use

import plugins.base
from constants.privileges import Privileges
from singletons.bot import Bot

bot = Bot()


@bot.command("system info")
@plugins.base.protected(Privileges.ADMIN_MANAGE_SERVERS)
@plugins.base.base
async def info() -> Tuple[str, ...]:
    """
    !system info

    :return: Some information about the bancho server currently running
    """
    result = await bot.bancho_api_client.system_info()
    return (
        f"Running delta v{result['delta_version']} "
        f"under Python {result['python_version']} ({result['interpreter_version']}) ",
        f"Bancho Uptime: {str(datetime.timedelta(seconds=result['uptime_seconds']))}",
        f"Running FokaBot v{Bot().VERSION}. "
        f"Scores server: {result['scores_server']['type']}, v{result['scores_server']['version']}",
    )


@bot.command("system shutdown")
@plugins.base.protected(Privileges.ADMIN_MANAGE_SERVERS)
@plugins.base.arguments(
    plugins.base.Arg("cancel", And(str, Use(lambda x: x.lower() == "cancel")), default=False, optional=True)
)
async def shutdown(cancel: bool) -> str:
    """
    !system shutdown [cancel]

    :return:
    """
    if cancel:
        if await bot.bancho_api_client.cancel_graceful_shutdown():
            return "Server shutdown cancelled."
        return "The server is not shutting down."

    if await bot.bancho_api_client.graceful_shutdown():
        return "The server will be restarted soon"
    return "The server is already restarting"


@bot.command("system recycle")
@plugins.base.protected(Privileges.ADMIN_MANAGE_SERVERS)
@plugins.base.base
async def recycle() -> str:
    if await bot.bancho_api_client.recycle():
        return "The server will be recycled very soon"
    return "The server is already recycling"
