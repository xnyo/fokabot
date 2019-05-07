from enum import auto

from constants import IntFlagHas


class Privileges(IntFlagHas):
    NONE: int = 0
    USER_PUBLIC: int = auto()
    USER_NORMAL: int = auto()
    USER_ALLOWED: int = USER_PUBLIC | USER_NORMAL
    USER_DONOR: int = auto()
    ADMIN_ACCESS_RAP: int = auto()
    ADMIN_MANAGE_USERS: int = auto()
    ADMIN_BAN_USERS: int = auto()
    ADMIN_SILENCE_USERS: int = auto()
    ADMIN_WIPE_USERS: int = auto()
    ADMIN_MANAGE_BEATMAPS: int = auto()
    ADMIN_MANAGE_SERVERS: int = auto()
    ADMIN_MANAGE_SETTINGS: int = auto()
    ADMIN_MANAGE_BETAKEYS: int = auto()
    ADMIN_MANAGE_REPORTS: int = auto()
    ADMIN_MANAGE_DOCS: int = auto()
    ADMIN_MANAGE_BADGES: int = auto()
    ADMIN_VIEW_RAP_LOGS: int = auto()
    ADMIN_MANAGE_PRIVILEGES: int = auto()
    ADMIN_SEND_ALERTS: int = auto()
    ADMIN_CHAT_MOD: int = auto()
    ADMIN_KICK_USERS: int = auto()
    USER_PENDING_VERIFICATION: int = auto()
    USER_TOURNAMENT_STAFF: int = auto()
    ADMIN_CAKER: int = auto()
