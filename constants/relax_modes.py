from enum import IntEnum


class RelaxMode(IntEnum):
    """
    Relax Mode Enumerator
    """
    BOTH: int = -1
    CLASSIC: int = 0
    RELAX: int = 1
