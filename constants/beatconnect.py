from enum import Enum


class Status(Enum):
    ALL = "all"
    RANKED = "ranked"
    APPROVED = "approved"
    QUALIFIED = "qualified"
    LOVED = "loved"
    UNRANKED = "unranked"


class Mode(Enum):
    ALL = "all"
    STANDARD = "std"
    TAIKO = "taiko"
    CTB = "ctb"
    MANIA = "mania"
