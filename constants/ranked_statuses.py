from enum import auto, IntEnum


class RankedStatus(IntEnum):
    """
    osu!api ranked Statuses
    """
    GRAVEYARD = -2
    WIP = auto()
    PENDING = auto()
    RANKED = auto()
    APPROVED = auto()
    QUALIFIED = auto()
    LOVED = auto()
