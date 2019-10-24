from constants.events import WsEvent
from constants.ranked_statuses import RankedStatus
from singletons.bot import Bot
from utils.osuapi import OsuAPIFatalError
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


class CheesegullLookupError(Exception):
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
        beatmap_set_id = 0
        bot.logger.debug(f"Beatmap changed in match #{data['id']} ({data['beatmap']['id']})")
        """

        """
        try:
            beatmap_response = await bot.cheesegull_api_client.get_beatmap(data["beatmap"]["id"])
            if beatmap_response is None:
                # Unknown beatmap
                raise CheesegullLookupError()
            set_response = await bot.cheesegull_api_client.get_set(beatmap_response["ParentSetID"])
            if set_response is None:
                # Unknown set ?
                raise CheesegullLookupError()
            if set_response["RankedStatus"] < RankedStatus.RANKED:
                # Cheesegull does not provide this beatmap, it must be downloaded through another mirror
                beatmap_set_id = beatmap_response["ParentSetID"]
        except CheesegullLookupError:
            try:
                response = await bot.osu_api_client.request("get_beatmaps", {"b": data['beatmap']['id'], "limit": 1})
                if not response:
                    # Unknown beatmap
                    return
                response = response[0]
                try:
                    beatmap_set_id = int(response["beatmapset_id"])
                except ValueError:
                    raise OsuAPIFatalError(f"Invalid beatmap set id ({response['beatmapset_id']})")
            except OsuAPIFatalError as e:
                # TODO: Sentry
                bot.logger.error(f"osu!api error ({e}). Failing silently.")
        if beatmap_set_id > 0:
            bot.send_message(
                f"Download [https://bloodcat.com/osu/s/{beatmap_set_id} " \
                f"{data['beatmap']['name']}] from Bloodcat",
                f"#multi_{data['id']}"
            )
