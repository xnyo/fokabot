from constants.events import WsEvent
from singletons.bot import Bot
import utils.beatmaps
from ws.messages import WsSubscribe, WsSubscribeMatch

bot = Bot()

beatmaps = {}


async def init():
    bot.logger.debug("Subscribing to all currently available multiplayer matches")
    for match in await bot.bancho_api_client.get_all_matches():
        bot.client.send(WsSubscribeMatch(match["id"]))
    bot.client.send(WsSubscribe(WsEvent.LOBBY))


@bot.client.on("msg:lobby_match_added")
async def match_added(**data):
    bot.logger.info(f"Match #{data['id']} added.")
    bot.client.send(WsSubscribeMatch(data['id']))
    await bot.client.wait("msg:subscribed")
    bot.logger.debug(f"Subscribed to match #{data['id']}")


@bot.client.on("msg:lobby_match_removed")
async def match_removed(**data):
    bot.logger.info(f"Match #{data['id']} removed.")

    # (we do not need to unsubscribe, the server will do it for us)

    if data["id"] in beatmaps:
        del beatmaps[data["id"]]


class CheesegullFaError(Exception):
    pass


@bot.client.on("msg:match_update")
async def match_updated(**data):
    bot.logger.debug(f"Got match update for match {data['id']}")

    if data["beatmap"]["id"] <= 0:
        # Changing beatmap right now
        return

    beatmap_changed = beatmaps.get(data["id"], 0) != data["beatmap"]["id"]
    beatmaps[data["id"]] = data["beatmap"]["id"]
    if beatmap_changed and data["beatmap"]["id"] > 0:
        bot.logger.debug(f"Beatmap changed in match #{data['id']} ({data['beatmap']['id']})")
        beatmap_set_id = await utils.beatmaps.get_beatmap_set_id(data["beatmap"]["id"], non_cheesegull_only=True)
        if beatmap_set_id is None:
            return
        if beatmap_set_id > 0:
            bot.send_message(
                await utils.beatmaps.get_download_message(beatmap_set_id, data["beatmap"]["name"]),
                f"#multi_{data['id']}"
            )
