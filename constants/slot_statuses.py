from enum import auto

from constants import IntFlagHas


class SlotStatus(IntFlagHas):
    OPEN = 1
    LOCKED = 2
    NOT_READY = auto()
    READY = auto()
    NO_MAP = auto()
    PLAYING = auto()
    COMPLETE = auto()
    QUIT = auto()
