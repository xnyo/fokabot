from enum import Enum, auto


class TournamentState(Enum):
    PRE_MATCH = auto()
    ROLLING = auto()
    BANNING = auto()
    PICKING_WARMUP = auto()
    WAITING_READY = auto()
    PLAYING = auto()
    PICKING = auto()
    CONFIRMING = auto()
    END = auto()
    MISSING_PLAYERS = auto()
