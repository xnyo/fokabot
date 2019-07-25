import functools
import operator

from enum import auto

from constants import IntFlagHas


class APIPrivileges(IntFlagHas):
    NONE = 0
    _READ_DEPRECATED = auto()
    READ_CONFIDENTIAL = auto()
    WRITE = auto()
    MANAGE_BADGES = auto()
    BETA_KEYS = auto()
    MANAGE_SETTINGS = auto()
    VIEW_USER_ADVANCED = auto()
    MANAGE_USER = auto()
    MANAGE_ROLES = auto()
    MANAGE_API_KEYS = auto()
    BLOG = auto()
    API_META = auto()
    BEATMAP = auto()
    BANCHO = auto()

    @staticmethod
    def all_privileges() -> "APIPrivileges":
        return functools.reduce(operator.or_, [x for x in APIPrivileges if x != APIPrivileges._READ_DEPRECATED])
