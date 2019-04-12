import random

from schema import Use, And

import plugins
from singletons.bot import Bot

bot = Bot()


@bot.command("roll")
@plugins.base
@plugins.arguments(plugins.Arg("number", And(Use(int), lambda x: x > 0), default=100))
async def roll(username: str, channel: str, number: int) -> str:
    """
    !roll <number>

    :param username:
    :param channel:
    :param number: max number, must > 0. Default: 100
    :return: a random number between 0 and some other number
    """
    return f"{username} rolls {random.randrange(0, number)} points!"


@bot.command("help")
@plugins.base
async def help_(username: str, channel: str, message: str) -> str:
    """
    !help

    :return: an help message with a link to FokaBot's command list
    """
    return "Click (here)[https://ripple.moe/index.php?p=16&id=4] for FokaBot's full command list"
