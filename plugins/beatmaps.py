from typing import Dict, Any

from constants.action import Action
from constants.events import WsEvent
from singletons.bot import Bot
import utils.beatmaps
from ws.messages import WsSubscribe, WsSubscribeMatch, WsChatMessage

bot = Bot()

multi_beatmaps = {}
spect_beatmaps = {}


async def init():
    bot.logger.debug("Subscribing to all currently available multiplayer matches")
    for match in await bot.bancho_api_client.get_all_matches():
        bot.client.send(WsSubscribeMatch(match["id"]))
    bot.client.send(WsSubscribe(WsEvent.LOBBY))
    bot.client.send(WsSubscribe(WsEvent.STATUS_UPDATES))


async def _notify_feature(destination: str) -> None:
    bot.client.send(
        WsChatMessage(
            "Hello! Ripple's chat bot here! I have been upgraded and now I will provide download links "
            "for unranked maps from beatconnect.io and Bloodcat automatically! You can manually request "
            "a beatconnect download link for the currently playing map with the !b command. This feature works both "
            "in multiplayer and spectator!",
            destination
        )
    )


@bot.client.on("msg:lobby_match_added")
async def match_added(**data):
    bot.logger.info(f"Match #{data['id']} added.")
    bot.client.send(WsSubscribeMatch(data['id']))
    await bot.client.wait("msg:subscribed")
    await _notify_feature(f"#multi_{data['id']}")
    bot.logger.debug(f"Subscribed to match #{data['id']}")


@bot.client.on("msg:chat_channel_added")
async def chat_channel_added(**data):
    if not data["name"].startswith("#spect_"):
        return
    await _notify_feature(data["name"])


@bot.client.on("msg:lobby_match_removed")
async def match_removed(**data):
    bot.logger.info(f"Match #{data['id']} removed.")

    # (we do not need to unsubscribe, the server will do it for us)

    try:
        del multi_beatmaps[data["id"]]
    except KeyError:
        pass


async def _send_beatmap_link(
    beatmap_id: int, beatmap_name: str, beatmap_cache_dict: Dict[Any, int], key: Any, target_channel: str
) -> None:
    if beatmap_id <= 0:
        # Changing beatmap right now
        return

    beatmap_changed = beatmap_cache_dict.get(key, 0) != beatmap_id
    beatmap_cache_dict[key] = beatmap_id
    if beatmap_changed and beatmap_id > 0:
        bot.logger.debug(f"Beatmap changed #{key} ({beatmap_id})")
        beatmap_set_id = await utils.beatmaps.get_beatmap_set_id(beatmap_id, non_cheesegull_only=True)
        if beatmap_set_id is None:
            return
        if beatmap_set_id > 0:
            bot.send_message(
                await utils.beatmaps.get_download_message(beatmap_set_id, beatmap_name),
                target_channel
            )


@bot.client.on("msg:match_update")
async def match_updated(**data):
    bot.logger.debug(f"Got match update for match {data['id']}")
    await _send_beatmap_link(
        beatmap_id=data["beatmap"]["id"],
        beatmap_name=data["beatmap"]["name"],
        beatmap_cache_dict=multi_beatmaps,
        key=data["id"],
        target_channel=f"#multi_{data['id']}"
    )


@bot.client.on("msg:status_update")
async def status_update(**data):
    if data["client"]["action"]["id"] != Action.PLAYING \
            or f"#spect_{data['client']['user_id']}" not in bot.joined_channels:
        bot.logger.debug("Non-spect status update, ignoring.")
        return
    await _send_beatmap_link(
        beatmap_id=data["client"]["action"]["beatmap"]["id"],
        beatmap_name=data["client"]["action"]["text"],
        beatmap_cache_dict=spect_beatmaps,
        key=data["client"]["user_id"],
        target_channel=f"#spect_{data['client']['user_id']}"
    )


@bot.client.on("msg:chat_channel_removed")
async def chat_channel_removed(name: str, **kwargs) -> None:
    if not name.startswith("#spect_"):
        return
    try:
        # This should never raise ValueError, theoretically
        user_id = int(name.split("_")[1])
        del spect_beatmaps[user_id]
        bot.logger.debug(f"Cleared spect beatmap cache for user {user_id}")
    except KeyError:
        pass
