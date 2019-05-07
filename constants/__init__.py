from typing import Union

from enum import IntFlag


class IntFlagHas(IntFlag):
    def has(self, v: Union[IntFlag, int]) -> bool:
        """
        Returns True if the privileges include the v privileges

        :param v:
        :return:
        """
        return (self.value & v) == v
