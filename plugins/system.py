from typing import Tuple
import datetime

from schema import And, Use

import plugins
from constants.privileges import Privileges
from singletons.bot import Bot

bot = Bot()


@bot.command("system info")
@plugins.base
@plugins.protected(Privileges.ADMIN_MANAGE_SERVERS)
async def info(username: str, channel: str, message: str) -> Tuple:
    """
    !system info

    :param username:
    :param channel:
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


@bot.command("system restart")
@plugins.base
@plugins.arguments(
    plugins.Arg("instant", And(str, Use(lambda x: x in ("now", "instant"))), default=False, optional=True)
)
@plugins.protected(Privileges.ADMIN_MANAGE_SERVERS)
async def restart(username: str, channel: str, instant: bool) -> str:
    """
    !system restart [now/instant]

    :param username:
    :param channel:
    :return:
    """
    r = await bot.bancho_api_client.graceful_shutdown()
    print(r)
    if r:
        return "The server will be restarted soon"
    return "The server is already restarting"
