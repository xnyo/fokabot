from enum import Enum


class SilenceUnit(Enum):
    SECONDS = "s"
    MINUTES = "m"
    HOURS = "h"
    DAYS = "d"

    @classmethod
    def exists(cls, value: str) -> bool:
        return any(value == item.value for item in cls)

    @property
    def seconds(self) -> int:
        if self == SilenceUnit.MINUTES:
            return 60
        if self == SilenceUnit.HOURS:
            return 3600
        if self == SilenceUnit.DAYS:
            return 86400
        return 1
