import logging
from collections import defaultdict
from datetime import datetime
from typing import Dict, Any, Set, Optional, List

from constants.game_modes import GameMode
from constants.misirlou_teams import MisirlouTeam
from constants.mods import Mod
from utils import general


class Beatmap:
    def __init__(self, id_: int, name: str, mods: Mod, tiebreaker: bool):
        self.id_ = id_
        self.name = name
        self.mods = mods
        self.tiebreaker = tiebreaker

    @classmethod
    def json_factory(cls, j: Dict[str, Any]) -> "Beatmap":
        return cls(
            id_=j["id"],
            name=j["name"],
            mods=Mod(j["mods"]),
            tiebreaker=j["tiebreaker"],
        )


class Tournament:
    def __init__(
        self, id_: int, name: str, abbreviation: str, game_mode: GameMode,
        team_size: int, pool: Dict[str, List[Beatmap]], tiebreaker: Beatmap,
    ):
        self.id_ = id_
        self.name = name
        self.abbreviation = abbreviation
        self.game_mode = game_mode
        self.team_size = team_size
        self.pool = pool
        self.tiebreaker = tiebreaker

    @property
    def is_solo(self) -> bool:
        return self.team_size == 1

    @classmethod
    def json_factory(cls, j: Dict[str, Any]) -> "Tournament":
        pool = defaultdict(list)
        tiebreaker = None
        for x in j["pool"]:
            m: Mod = Mod(x["mods"])
            beatmap = Beatmap.json_factory(x)
            if x["tiebreaker"]:
                tiebreaker = beatmap
            else:
                pool[m].append(beatmap)
        assert tiebreaker is not None, "No tiebreaker in this pool"
        logging.debug(pool)
        return cls(
            id_=j["id"],
            name=j["name"],
            abbreviation=j["abbreviation"],
            game_mode=GameMode(j["game_mode"]),
            team_size=j["team_size"],
            pool=pool,
            tiebreaker=tiebreaker
        )


class Team:
    def __init__(self, id_: int, name: int, members: List[int], captain: int, enum: MisirlouTeam):
        self.id_ = id_
        self.name = name
        self.members = members
        self.captain = captain
        self.enum = enum

        assert self.captain in self.members, "Captain not in team members"
        assert captain is not None, "Team with no captain"

        self.members_in_match: Set[int] = set()
        self._roll: Optional[int] = None

    @classmethod
    def json_factory(cls, j: Dict[str, Any], enum: MisirlouTeam) -> "Team":
        return cls(id_=j["id"], name=j["name"], members=j["members"], captain=j["captain"], enum=enum)

    @property
    def captain_in_match(self) -> bool:
        return self.captain in self.members_in_match

    @property
    def roll(self) -> Optional[int]:
        return self._roll

    @roll.setter
    def roll(self, v: int):
        if self.roll is not None:
            raise RuntimeError("Cannot set the roll twice")
        self._roll = v


class Match:
    def __init__(self, id_: int, when: datetime, tournament: Tournament, team_a: Team, team_b: Team, password: str):
        self.id_ = id_
        self.when = when
        self.tournament = tournament
        self.team_a = team_a
        self.team_b = team_b

        self.bancho_match_id = None
        self.usernames: Dict[int, str] = {}
        self.password: str = password

    @classmethod
    def json_factory(cls, j: Dict[str, any], password: str) -> "Match":
        return cls(
            id_=j["id"],
            when=general.rfc3339_to_datetime(j["timestamp"]),
            team_a=Team.json_factory(j["team_a"], enum=MisirlouTeam.A),
            team_b=Team.json_factory(j["team_b"], enum=MisirlouTeam.B),
            tournament=Tournament.json_factory(j["tournament"]),
            password=password,
        )

    @property
    def _both_rolled(self) -> bool:
        return self.team_a.roll is not None and self.team_b.roll is not None

    @property
    def roll_winner(self) -> Optional[Team]:
        if not self._both_rolled:
            return None
        return self.team_a if self.team_a.roll > self.team_b.roll else self.team_b

    @property
    def roll_loser(self) -> Optional[Team]:
        if not self._both_rolled:
            return None
        return self.team_enum_to_team(self.roll_winner.enum.other)

    def is_player(self, user_id: int) -> bool:
        """

        :return: True if user_id is a player in this match
        """
        return user_id in self.team_a.members + self.team_b.members

    def get_user_team(self, user_id: int) -> Optional[Team]:
        if user_id in self.team_a.members:
            return self.team_a
        if user_id in self.team_b.members:
            return self.team_b
        return None

    @property
    def chat_channel_name(self) -> str:
        return f"#multi_{self.bancho_match_id}"

    def team_enum_to_team(self, team: MisirlouTeam) -> Team:
        if team == MisirlouTeam.A:
            return self.team_a
        elif team == MisirlouTeam.B:
            return self.team_b
        raise ValueError(f"Invalid team {team}")

    def captain_or_team_name(self, team: Team) -> str:
        if team.captain_in_match:
            return self.usernames[team.captain]
        return f"Team {team.name}"

    def captain_or_team_members(self, team: Team) -> str:
        if team.captain_in_match:
            return self.usernames[team.captain]
        return (", ".join(self.usernames[x] for x in team.members_in_match)) + f" ({team.name}'s members)"


class MisirlouMatch:
    def __init__(self, misirlou_data: Dict[str, Any], bancho_match_id: int):
        self.misirlou_data: Dict[str, Any] = misirlou_data
        self.bancho_match_id: int = bancho_match_id
        # Used to detect new users
        self.known_api_identifiers: Set[str] = set()

        self.players_in_match: Dict[MisirlouTeam, Set[int]] = {MisirlouTeam.A: set(), MisirlouTeam.B: set()}
        self.rolls: Dict[MisirlouTeam, Optional[int]] = {MisirlouTeam.A: None, MisirlouTeam.B: None}
        self.usernames: Dict[int, str] = {}

    @property
    def roll_winner(self) -> Optional[MisirlouTeam]:
        if self.rolls[MisirlouTeam.A] is None or self.rolls[MisirlouTeam.B] is None:
            return None
        logging.debug(self.rolls)
        return MisirlouTeam.A if self.rolls[MisirlouTeam.A] > self.rolls[MisirlouTeam.B] else MisirlouTeam.B

    def is_player(self, user_id: int) -> bool:
        """

        :return: True if user_id is a player in this match
        """
        return user_id in self.misirlou_data["team_a"]["members"] + self.misirlou_data["team_b"]["members"]

    def is_team_player(self, team: MisirlouTeam, user_id: int) -> bool:
        return user_id in self.misirlou_data["team_a" if team == MisirlouTeam.A else "team_b"]["members"]

    def get_user_team(self, user_id: int) -> Optional[MisirlouTeam]:
        if self.is_team_player(MisirlouTeam.A, user_id):
            return MisirlouTeam.A
        if self.is_team_player(MisirlouTeam.B, user_id):
            return MisirlouTeam.B
        return None

    def get_team_data(self, team: MisirlouTeam) -> Optional[Dict[str, Any]]:
        # TODO: ??? I hate working with dicts etc
        return self.misirlou_data[f"team_{team.value}"]

    @property
    def team_size(self) -> int:
        return self.misirlou_data["tournament"]["team_size"]

    @property
    def tournament_name(self) -> str:
        return self.misirlou_data["tournament"]["name"]

    @property
    def tournament_abbreviation(self) -> str:
        return self.misirlou_data["tournament"]["abbreviation"]

    @property
    def chat_channel_name(self) -> str:
        return f"#multi_{self.bancho_match_id}"

    def is_captain_in_match(self, team: MisirlouTeam):
        return self.get_team_data(team)["captain"] in self.players_in_match[team]

    @property
    def is_solo(self) -> bool:
        return self.misirlou_data["tournament"]["team_size"] == 1

    def username_or_team_name(self, team: MisirlouTeam) -> str:
        if self.is_captain_in_match(team):
            return self.usernames[self.get_team_data(team)["captain"]]
        return f"Team {self.get_team_data(team)['name']}"
