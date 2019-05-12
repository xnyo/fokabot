from enum import IntEnum, auto


class GameMode(IntEnum):
    """
    Game Mode Enumerator
    """
    STANDARD: int = 0
    TAIKO: int = auto()
    CATCH_THE_BEAT: int = auto()
    MANIA: int = auto()

    def for_db(self) -> str:
        """
        Returns the current game mode string, for db (std/taiko/ctb/mania)

        :return:
        """
        return _FOR_DB[self.value]

    @classmethod
    def np_factory(cls, game_mode_str: str) -> "GameMode":
        """
        Factory method that returns a new GameMode instance
        from a str from a /np message from the osu! client

        :param game_mode_str: game mode str from /np message (eg: 'CatchTheBeat')
        :return:
        """
        if game_mode_str in _NP.keys():
            return _NP[game_mode_str]
        return GameMode.STANDARD


_FOR_DB = {
    GameMode.STANDARD: "std",
    GameMode.TAIKO: "taiko",
    GameMode.CATCH_THE_BEAT: "ctb",
    GameMode.MANIA: "mania"
}
_NP = {
    "CatchTheBeat": GameMode.CATCH_THE_BEAT,
    "Taiko": GameMode.TAIKO,
    "osu!mania": GameMode.MANIA
}
