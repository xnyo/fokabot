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

    def __str__(self) -> str:
        """
        Returns a readable representation of the current game mode
        (osu!standard, osu!taiko, osu!catch, osu!mania)

        :return:
        """
        return _READABLE[self.value]

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

    @classmethod
    def db_factory(cls, db_str: str) -> "GameMode":
        """
        Factory method that returns a new GameMode instance
        from a str containing a db-like game mode (std/taiko/ctb/mania).
        Returns `GameMode.STANDARD` if db_str does not correspond to a valid game mode

        :param db_str: game mode str from /np message (eg: 'CatchTheBeat')
        :return:
        """
        for k, v in _FOR_DB.items():
            if v == db_str:
                return k
        return GameMode.STANDARD


_FOR_DB = {
    GameMode.STANDARD: "std",
    GameMode.TAIKO: "taiko",
    GameMode.CATCH_THE_BEAT: "ctb",
    GameMode.MANIA: "mania"
}
_READABLE = {
    GameMode.STANDARD: "osu!standard",
    GameMode.TAIKO: "osu!taiko",
    GameMode.CATCH_THE_BEAT: "osu!catch",
    GameMode.MANIA: "osu!mania"
}
_NP = {
    "CatchTheBeat": GameMode.CATCH_THE_BEAT,
    "Taiko": GameMode.TAIKO,
    "osu!mania": GameMode.MANIA
}
