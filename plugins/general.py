from typing import Dict
import random
from aiotinydb import AIOTinyDB

from schema import Use, And, Schema
from tinydb import Query, where

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
        results = db.table("faq").search(where("topic") == params["topic"])
        if results:
            return results[0]["response"]
        else:
            return "No such FAQ topic."


@bot.command("modfaq")
@base
@arguments(
    Arg("topic", Schema(str)),
    Arg("response", Schema(str), rest=True),
)
async def mod_faq(username: str, channel: str, params: Dict[str, str]):
    async with AIOTinyDB(".db.json") as db:
        db.table("faq").upsert({"topic": params["topic"], "response": params["response"]}, where("topic") == params["topic"])
    return f"FAQ topic '{params['topic']}' updated!"


@bot.command("lsfaq")
@base
async def ls_faq(*_, **__):
    async with AIOTinyDB(".db.json") as db:
        return f"Available FAQ topics: {', '.join(x['topic'] for x in db.table('faq').all())}"
