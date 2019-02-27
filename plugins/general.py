import random

from schema import Use, And

from plugins import arguments, Arg, base
from singletons.bot import Bot

bot = Bot()


@bot.command("roll")
@base
@arguments(Arg("number", And(Use(int), lambda x: x > 0), default=100))
async def roll(username: str, _: str, number: int) -> str:
    """
    !roll <number>

    :param username:
    :param _:
    :param number: max number, must > 0. Default: 100
    :return: a random number between 0 and some other number
    """
    return f"{username} rolls {random.randrange(0, number)} points!"


@bot.command("help")
@base
async def help_(*_, **__) -> str:
    """
    !help

    :return: an help message with a link to FokaBot's command list
    """
    return "Click (here)[https://ripple.moe/index.php?p=16&id=4] for FokaBot's full command list"
