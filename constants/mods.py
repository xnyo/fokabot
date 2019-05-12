from functools import reduce

from enum import IntFlag


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
    KEY_MODS = KEY2 | KEY3 | KEY1 | KEY_COOP | KEY9 | KEY8 | KEY7 | KEY6 | KEY5 | KEY4
    FREE_MOD_ALLOWED = KEY_MODS | FADE_IN | RELAX2 | SPUN_OUT | FLASHLIGHT | RELAX | SUDDEN_DEATH | HARD_ROCK | HIDDEN | EASY | NO_FAIL

    def __str__(self) -> str:
        """
        Returns a readable and short representation
        of the mods represented by this object.

        :return: mod combination string. Eg: 'HDDT', 'NOMOD'
        """
        return "".join(_ACRONYMS[x] for x in Mod if self & x > 0 and x in _ACRONYMS)

    @classmethod
    def np_factory(cls, mods_str: str) -> "Mod":
        """
        Factory method that returns a new Mod instance
        from a str from a /np message from the osu! client.
        If multiple mods are present in mods_str, they're combined.
        Does not check if the mod combination is valid.

        :param mods_str: game mode str from /np message (eg: '+HardRock +DoubleTime')
        :return: Mod instance
        """
        return reduce(
            lambda x, y: x | y,
            (_NP.get(x.lstrip("+-"), Mod.NO_MOD) for x in mods_str.strip().split(" "))
        )


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
