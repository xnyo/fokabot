import datetime
from typing import Optional

import logging

from constants.game_modes import GameMode
from constants.mods import Mod
from utils.cache import CacheElement, CacheStorage, SafeUsernamesDict


class NpInfo(CacheElement):
    def __init__(
        self, beatmap_id: int, game_mode: Optional[GameMode] = None,
        mods: Optional[Mod] = None, accuracy: Optional[float] = None
    ):
        self.beatmap_id = beatmap_id
        self.game_mode = game_mode
        self.mods = mods
        self.accuracy = accuracy

        # We call this later so we don't update the refresh datetime for all the lines above
        super(NpInfo, self).__init__(expiration_delta=datetime.timedelta(minutes=3))


class NpStorage(CacheStorage):
    logger = logging.getLogger("np_storage")

    def __init__(self):
        super(NpStorage, self).__init__()
        self._data: SafeUsernamesDict[str, NpInfo] = SafeUsernamesDict()
