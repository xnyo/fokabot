from schema import And, Use

from constants.mods import Mod, ModSpecialMode

StrippedString = And(str, Use(lambda x: x.strip()))
NonEmptyString: And = And(StrippedString, lambda x: bool(x))
ModStringSingle = And(str, Use(Mod.short_factory))
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