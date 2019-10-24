from typing import Optional

from constants.ranked_statuses import RankedStatus
from singletons.bot import Bot
from utils.osuapi import OsuAPIError

bot = Bot()


class CheesegullLookupError(Exception):
    pass


async def get_beatmap_set_id(beatmap_id: int, non_cheesegull_only: bool = True) -> Optional[int]:
    """
    Gets a beatmap set id from a beatmap id.
    It'll try to use cheesegull first, in case it fails it'll use the osu!api

    :param beatmap_id: id of the beatmap
    :param non_cheesegull_only: if True, return the beatmap id only if
                                the map is available on cheesegull (and it's ranked),
                                and return None otherwise. If False, a link will always
                                be returned (if it's available)
    :return: the beatmap set id, or None
    """
    try:
        beatmap_response = await bot.cheesegull_api_client.get_beatmap(beatmap_id)
        if beatmap_response is None:
            # Unknown beatmap
            raise CheesegullLookupError()
        set_response = await bot.cheesegull_api_client.get_set(beatmap_response["ParentSetID"])
        if set_response is None:
            # Unknown set ?
            raise CheesegullLookupError()
        if not non_cheesegull_only or set_response["RankedStatus"] < RankedStatus.RANKED:
            return beatmap_response["ParentSetID"]
    except CheesegullLookupError:
        try:
            response = await bot.osu_api_client.request("get_beatmaps", {"b": beatmap_id, "limit": 1})
            if not response:
                # Unknown beatmap
                return
            response = response[0]
            try:
                return int(response["beatmapset_id"])
            except ValueError:
                raise OsuAPIError(f"Invalid beatmap set id ({response['beatmapset_id']})")
        except OsuAPIError as e:
            # TODO: Sentry
            bot.logger.error(f"osu!api error ({e}). Failing silently.")
    return None
