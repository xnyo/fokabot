from typing import Dict, Any
import random

from schema import Use, And

from plugins import arguments, Arg, public_only
from singletons.bot import Bot

bot = Bot()


@bot.command("roll")
@arguments(
    Arg("number", And(Use(int), lambda x: x > 0), default=100)
)
@public_only
async def roll(username: str, channel: str, params: Dict[str, Any]):
    return f"{username} rolls {random.randrange(0, params['number'])} points!"
