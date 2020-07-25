import collections
from typing import Iterable, Dict

import operator
from functools import reduce

from enum import IntFlag, auto


class ModSpecialMode(IntFlag):
    NORMAL = 0
    FREE_MODS = auto()


class Mod(IntFlag):
    NO_MOD = 0
    NO_FAIL = 1
    EASY = 2
    TOUCHSCREEN = 4
    HIDDEN = 8
    HARD_ROCK = 16
    SUDDEN_DEATH = 32
    DOUBLE_TIME = 64
    RELAX = 128
    HALF_TIME = 256
    NIGHTCORE = 512
    FLASHLIGHT = 1024
    AUTOPLAY = 2048
    SPUN_OUT = 4096
    RELAX2 = 8192
    PERFECT = 16384
    KEY4 = 32768
    KEY5 = 65536
    KEY6 = 131072
    KEY7 = 262144
    KEY8 = 524288
    KEYMOD = 1015808
    FADE_IN = 1048576
    RANDOM = 2097152
    LASTMOD = 4194304
    KEY9 = 16777216
    KEY_COOP = 33554432
    KEY1 = 67108864
    KEY3 = 134217728
    KEY2 = 268435456
    SCOREV2 = 536870912

    # Special, ripple only
    # It's not possible to extend enums in Python, so we have to do it this way...
    FREE_MODS = 1073741824

    KEY_MODS = KEY2 | KEY3 | KEY1 | KEY_COOP | KEY9 | KEY8 | KEY7 | KEY6 | KEY5 | KEY4
    FREE_MOD_ALLOWED = KEY_MODS | FADE_IN | RELAX2 | SPUN_OUT | FLASHLIGHT | RELAX | SUDDEN_DEATH | HARD_ROCK | HIDDEN | EASY | NO_FAIL

    def _str(self, acronyms: Dict["Mod", str]) -> str:
        if self == 0 and Mod.NO_MOD in acronyms:
            return acronyms[Mod.NO_MOD]
        return "".join(acronyms[x] for x in Mod if self & x > 0 and x in acronyms)

    @property
    def tournament_str(self) -> str:
        """
        Returns a readable and short representation
        of the mods represented by this object for tournaments.

        :return: mod combination string. Eg: 'HDDT', 'NM', 'FM'...
        """
        if self & Mod.FREE_MODS > 0:
            # Free mods
            # We want FMXXYY only if != nomod, we don't want FMNM!
            rest = self.normalized
            extra = "" if rest == Mod.NO_MOD else str(Mod(rest))
            return "FM" + extra
        # Normal
        return self._str(_TOURNAMENT_ACRONYMS)

    @property
    def normalized(self) -> "Mod":
        """
        Returns a new Mod, with FREE_MODS filtered out
        Useful only for misirlou tournaments

        :return: self, but without FREE_MODS
        """
        return Mod(self & ~Mod.FREE_MODS)

    def __str__(self) -> str:
        """
        Returns a readable and short representation
        of the mods represented by this object.

        :return: mod combination string. Eg: 'HDDT', 'NOMOD'
        """
        return self._str(_ACRONYMS)

    @classmethod
    def np_factory(cls, mods_str: str) -> "Mod":
        """
        Factory method that returns a new Mod instance
        from a str from a /np message from the osu! client.
        If multiple mods are present in mods_str, they're combined.
        Does not check if the mod combination is valid.

        :param mods_str: mods str from /np message (eg: '+HardRock +DoubleTime')
        :return: Mod instance
        """
        return reduce(
            operator.or_,
            (_NP.get(x.lstrip("+-"), Mod.NO_MOD) for x in mods_str.strip().split(" "))
        )

    @classmethod
    def short_factory(cls, readable_mods: str) -> "Mod":
        """
        Returns a Mod instance from a string of short mods. With no spaces, case-insensitive. (eg: HDDTHR).

        :param readable_mods: string containing the mods
        :return:
        """
        readable_mods = readable_mods.strip()
        return reduce(
            operator.or_,
            (_MODS.get(readable_mods[i:i + 2].upper(), Mod.NO_MOD) for i in range(0, len(readable_mods), 2))
        )

    @classmethod
    def iterable_factory(cls, readable_mods: Iterable[str]) -> "Mod":
        """
        Creates a Mod instance from an iterable of readable mods acronyms. Case-insensitive.
        Eg: ["HD", "DT"]

        :param readable_mods: iterable of readable mods
        :return: Mod instance
        """
        return reduce(operator.or_, (_MODS.get(x.strip().upper(), Mod.NO_MOD) for x in readable_mods))


_ACRONYMS = {
    Mod.NO_MOD: "NOMOD",
    Mod.NO_FAIL: "NF",
    Mod.EASY: "EZ",
    Mod.HIDDEN: "HD",
    Mod.HARD_ROCK: "HR",
    Mod.SUDDEN_DEATH: "SD",
    Mod.DOUBLE_TIME: "DT",
    Mod.RELAX: "RX",
    Mod.HALF_TIME: "HT",
    # Mod.NIGHTCORE: ,
    Mod.FLASHLIGHT: "FL",
    # Mod.AUTOPLAY: "auto",
    Mod.SPUN_OUT: "SO",
    Mod.RELAX2: "AP",
    Mod.PERFECT: "PF",
    Mod.KEY4: "4K",
    Mod.KEY5: "5K",
    Mod.KEY6: "6K",
    Mod.KEY7: "7K",
    Mod.KEY8: "8K",
    Mod.FADE_IN: "FI",
    # Mod.LASTMOD: 4194304,
    Mod.KEY9: "9K",
    # Mod.KEY_COOP: 33554432,
    Mod.KEY1: "1K",
    Mod.KEY3: "3K",
    Mod.KEY2: "2K",
    # Mod.SCOREV2: "score v2",
}

_TOURNAMENT_ACRONYMS = _ACRONYMS.copy()
_TOURNAMENT_ACRONYMS[Mod.NO_MOD] = "NM"

_MODS = {v: k for k, v in _ACRONYMS.items()}
_NP = {
    "Easy": Mod.EASY,
    "NoFail": Mod.NO_FAIL,
    "Hidden": Mod.HIDDEN,
    "HardRock": Mod.HARD_ROCK,
    "Nightcore": Mod.DOUBLE_TIME,
    "DoubleTime": Mod.DOUBLE_TIME,
    "HalfTime": Mod.HALF_TIME,
    "Flashlight": Mod.FLASHLIGHT,
    "SpunOut": Mod.SPUN_OUT
}
