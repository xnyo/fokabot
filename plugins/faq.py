from aiotinydb import AIOTinyDB

from schema import Schema
from tinydb import where

from plugins import arguments, Arg, base
from singletons.bot import Bot


bot = Bot()


@bot.command("faq")
@base
@arguments(Arg("topic", Schema(str)))
async def faq(username: str, channel: str, topic: str) -> str:
    """
    !faq <topic>

    :param username:
    :param channel:
    :param topic: FAQ topic name. Will get it from FokaBot's tinydb
    :return: the topic content, if it exists, or an error message
    """
    async with AIOTinyDB(".db.json") as db:
        results = db.table("faq").search(where("topic") == topic)
        if results:
            return results[0]["response"]
        else:
            return "No such FAQ topic."


@bot.command("modfaq")
@base
@arguments(
    Arg("topic", Schema(str)),
    Arg("new_response", Schema(str), rest=True),
)
async def mod_faq(username: str, channel: str, topic: str, new_response: str) -> str:
    """
    !modfaq <topic> <new_response>
    Edits an existing topic in tinydb. Doesn't do anything if the specified topic does not exist.

    :param username:
    :param channel:
    :param topic: the name of the FAQ topic to edit
    :param new_response: the new response
    :return: success message
    """
    async with AIOTinyDB(".db.json") as db:
        db.table("faq").upsert({"topic": topic, "response": new_response}, where("topic") == topic)
    return f"FAQ topic '{topic}' updated!"


@bot.command("lsfaq")
@base
async def ls_faq(username: str, channel: str) -> str:
    """
    !lsfaq

    :param username:
    :param channel:
    :return: A list of all available FAQ topics
    """
    async with AIOTinyDB(".db.json") as db:
        return f"Available FAQ topics: {', '.join(x['topic'] for x in db.table('faq').all())}"


@bot.command("delfaq")
@base
@arguments(Arg("topic", Schema(str)))
async def del_faq(username: str, channel: str, topic: str) -> str:
    """
    !delfaq <topic>
    Deletes a FAQ topic from tinydb, if it exists.

    :param username:
    :param channel:
    :param topic: the name of the topic to delete
    :return: a success message
    """
    async with AIOTinyDB(".db.json") as db:
        db.table("faq").remove(where("topic") == topic)
    return f"FAQ topic '{topic}' deleted!"
