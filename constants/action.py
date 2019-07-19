from enum import IntEnum, auto


class Action(IntEnum):
    IDLE = 0
    AFK = auto()
    PLAYING = auto()
    EDITING = auto()
    MODDING = auto()
    MULTIPLAYER = auto()
    WATCHING = auto()
    _UNKNOWN_1 = auto()
    TESTING = auto()
    SUBMITTING = auto()
    PAUSED = auto()
    LOBBY = auto()
    MULTIPLAYING = auto()
    OSU_DIRECT = auto()
    _UNKNOWN_2 = auto()

    @property
    def playing(self) -> bool:
        return self in (Action.PLAYING, Action.MULTIPLAYING)
