import random

from schema import Use, And

from plugins import arguments, Arg, base
from singletons.bot import Bot

bot = Bot()


@bot.command("roll")
@base
@arguments(Arg("number", And(Use(int), lambda x: x > 0), default=100))
async def roll(username: str, channel: str, number: int):
    return f"{username} rolls {random.randrange(0, number)} points!"


@bot.command("help")
@base
async def help_(*_, **__):
    return "Click (here)[https://ripple.moe/index.php?p=16&id=4] for FokaBot's full command list"
