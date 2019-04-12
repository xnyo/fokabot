from typing import Tuple
import datetime

import plugins
from singletons.bot import Bot

bot = Bot()


@bot.command("system info")
@plugins.base
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
