from enum import auto, IntEnum


class Team(IntEnum):
    """
    Multiplayer match team enum
    """
    NEUTRAL = 0
    BLUE = auto()
    RED = auto()
