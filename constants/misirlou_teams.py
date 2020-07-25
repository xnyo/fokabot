from enum import Enum

from constants.teams import Team


class MisirlouTeam(Enum):
    A = "a"
    B = "b"

    @property
    def bancho_team(self) -> Team:
        return Team.BLUE if self == MisirlouTeam.A else Team.RED

    @property
    def other(self):
        return MisirlouTeam.A if self == MisirlouTeam.B else MisirlouTeam.B
