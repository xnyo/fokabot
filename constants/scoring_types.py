from enum import auto, IntEnum


class ScoringType(IntEnum):
    """
    Multiplayer scoring rules
    """
    SCORE = 0
    ACCURACY = auto()
    COMBO = auto()
    SCORE_V2 = auto()
