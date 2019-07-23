from enum import IntEnum, auto


class TeamType(IntEnum):
    """
    Multiplayer team rules
    """
    HEAD_TO_HEAD = 0
    TAG_COOP = auto()
    TEAM_VS = auto()
    TAG_TEAM_VS = auto()
