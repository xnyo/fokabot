from typing import Optional, Union

from constants.game_modes import GameMode
from constants.mods import Mod
from utils import autojson


class NpInfo(autojson.Slots):
    __slots__ = "beatmap_id", "game_mode", "mods", "accuracy"

    def __init__(
        self, beatmap_id: int, game_mode: Optional[Union[GameMode, int]] = None,
        mods: Optional[Union[Mod, int]] = None, accuracy: Optional[float] = None
    ):
        self.beatmap_id = beatmap_id
        if type(game_mode) is not GameMode:
            game_mode = GameMode(game_mode)
        self.game_mode = game_mode
        if type(mods) is not Mod:
            mods = Mod(mods)
        self.mods = mods
        self.accuracy = accuracy
