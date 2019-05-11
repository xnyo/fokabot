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


_FOR_DB = {
    GameMode.STANDARD: "std",
    GameMode.TAIKO: "taiko",
    GameMode.CATCH_THE_BEAT: "ctb",
    GameMode.MANIA: "mania"
}
