from aiotinydb import AIOTinyDB

from schema import Schema
from tinydb import where

import plugins.base
from constants.privileges import Privileges
from singletons.bot import Bot


bot = Bot()


@bot.command("faq")
@plugins.base.arguments(plugins.base.Arg("topic", Schema(str)))
async def faq(topic: str) -> str:
    """
    !faq <topic>

    :param topic: FAQ topic name. Will get it from FokaBot's tinydb
    :return: the topic content, if it exists, or an error message
    """
    async with AIOTinyDB(bot.tinydb_path) as db:
        results = db.table("faq").search(where("topic") == topic)
        if results:
            return results[0]["response"]
        else:
            return "No such FAQ topic."


@bot.command("modfaq")
@plugins.base.protected(Privileges.ADMIN_CHAT_MOD)
@plugins.base.arguments(
    plugins.base.Arg("topic", Schema(str)),
    plugins.base.Arg("new_response", Schema(str), rest=True),
)
async def mod_faq(topic: str, new_response: str) -> str:
    """
    !modfaq <topic> <new_response>
    Edits an existing topic in tinydb. Doesn't do anything if the specified topic does not exist.

    :param topic: the name of the FAQ topic to edit
    :param new_response: the new response
    :return: success message
    """
    async with AIOTinyDB(bot.tinydb_path) as db:
        db.table("faq").upsert({"topic": topic, "response": new_response}, where("topic") == topic)
    return f"FAQ topic '{topic}' updated!"


@bot.command("lsfaq")
@plugins.base.base
async def ls_faq() -> str:
    """
    !lsfaq

    :return: A list of all available FAQ topics
    """
    async with AIOTinyDB(bot.tinydb_path) as db:
        return f"Available FAQ topics: {', '.join(x['topic'] for x in db.table('faq').all())}"


@bot.command("delfaq")
@plugins.base.protected(Privileges.ADMIN_CHAT_MOD)
@plugins.base.arguments(plugins.base.Arg("topic", Schema(str)))
async def del_faq(topic: str) -> str:
    """
    !delfaq <topic>
    Deletes a FAQ topic from tinydb, if it exists.

    :param topic: the name of the topic to delete
    :return: a success message
    """
    async with AIOTinyDB(bot.tinydb_path) as db:
        db.table("faq").remove(where("topic") == topic)
    return f"FAQ topic '{topic}' deleted!"
