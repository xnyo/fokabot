from typing import Dict
import random
from aiotinydb import AIOTinyDB

from schema import Use, And, Schema

from plugins import arguments, Arg, errors, base
from singletons.bot import Bot

bot = Bot()


@bot.command("roll")
@base
@arguments(
    Arg("number", And(Use(int), lambda x: x > 0), default=100)
)
async def roll(username: str, channel: str, params: Dict[str, int]):
    return f"{username} rolls {random.randrange(0, params['number'])} points!"


@bot.command("help")
@base
async def help_(*_, **__):
    return "Click (here)[https://ripple.moe/index.php?p=16&id=4] for FokaBot's full command list"


@bot.command("faq")
@base
@arguments(
    Arg("topic", Schema(str))
)
async def faq(username: str, channel: str, params: Dict[str, str]):
    async with AIOTinyDB(".db.json") as db:
        print(db.table("faq").all())


@bot.command("modfaq")
@base
@arguments(
    Arg("topic", Schema(str)),
    Arg("response", Schema(str), rest=True),
)
async def mod_faq(username: str, channel: str, params: Dict[str, str]):
    async with AIOTinyDB(".db.json") as db:
        print(db.table("faq").all())
