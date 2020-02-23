from schema import And, Use

from constants.mods import Mod, ModSpecialMode
from constants.game_modes import GameMode

StrippedString = And(str, Use(lambda x: x.strip()))
NonEmptyString: And = And(StrippedString, lambda x: bool(x))
ModStringSingle = And(str, Use(lambda x: Mod.RELAX if x.lower() == "relax" else Mod.short_factory(x)))
ModStringMultipleAndSpecialMode = And(
    str,
    Use(lambda x: x.split(" ")),
    Use(
        lambda x: (
            (ModSpecialMode.FREE_MODS if any(y == "freemod" for y in x) else ModSpecialMode.NORMAL),
            Mod.iterable_factory(x)
        )
    )
)
GameModeString = And(str, Use(GameMode.db_factory))
