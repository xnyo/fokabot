from typing import Tuple
import datetime

from schema import And, Use

import plugins
from constants.privileges import Privileges
from singletons.bot import Bot
from utils import general

bot = Bot()


@bot.command("system info")
@plugins.base
@plugins.protected(Privileges.ADMIN_MANAGE_SERVERS)
async def info(username: str, channel: str, message: str, **kwargs) -> Tuple:
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


@bot.command("system shutdown")
@plugins.base
@plugins.arguments(
    plugins.Arg("cancel", And(str, Use(lambda x: x.lower() == "cancel")), default=False, optional=True)
)
@plugins.protected(Privileges.ADMIN_MANAGE_SERVERS)
async def shutdown(username: str, channel: str, cancel: bool, **kwargs) -> str:
    """
    !system shutdown [cancel]

    :param username:
    :param channel:
    :param cancel:
    :return:
    """
    if cancel:
        if await bot.bancho_api_client.cancel_graceful_shutdown():
            return "Server shutdown cancelled."
        return "The server is not shutting down."

    if await bot.bancho_api_client.graceful_shutdown():
        return "The server will be restarted soon"
    return "The server is already restarting"


@bot.command("system privcache info")
@plugins.base
@plugins.protected(Privileges.ADMIN_MANAGE_SERVERS)
async def privcache_info(username: str, channel: str, *args, **kwargs) -> str:
    """
    !system privcache info

    :return: Displays some information about the privileges cache
    """
    return f"Users in privileges cache ({len(bot.privileges_cache)}): {', '.join(x for x in bot.privileges_cache._data.keys())}."


@bot.command("system privcache remove")
@plugins.base
@plugins.arguments(
    plugins.Arg("target_username", And(str, Use(general.safefify_username))),
)
@plugins.protected(Privileges.ADMIN_MANAGE_SERVERS)
async def privcache_remove(username: str, channel: str, target_username: str, **kwargs) -> str:
    """
    !system privcache remove <username>

    :param username: Username of the user that will be removed from the cache
    :return:
    """
    if target_username not in bot.privileges_cache:
        return f"{target_username} is not in the privileges cache."
    del bot.privileges_cache[target_username]
    return f"{target_username} has been removed from the privileges cache."


@bot.command("system privcache purge")
@plugins.base
@plugins.protected(Privileges.ADMIN_MANAGE_SERVERS)
async def privcache_purge(username: str, channel: str, *args, **kwargs) -> str:
    """
    !system privcache purge
    Purges the privileges cache

    :return:
    """
    old_size = len(bot.privileges_cache)
    bot.privileges_cache.purge()
    return f"Privileges size purged! ({old_size} -> {len(bot.privileges_cache)})"
