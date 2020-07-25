import asyncio
import logging
import re
from typing import Dict, Any, Optional, Callable

import plugins.base
from constants.misirlou_teams import MisirlouTeam
from constants.privileges import Privileges
from constants.scoring_types import ScoringType
from constants.slot_statuses import SlotStatus
from constants.team_types import TeamType
from singletons.bot import Bot
from utils import general, misirlou
from utils.rippleapi import BanchoApiBeatmap

bot = Bot()


def resolve_tournament_only(f: Callable) -> Callable:
    async def wrapper(match: Dict[str, Any], **kwargs):
        if match["id"] not in bot.tournament_matches.keys():
            # Not a tournament match, abort
            return
        return await f(match=match, tournament_match=bot.tournament_matches[match["id"]], **kwargs)
    return wrapper


async def create_misirlou_match(misirlou_match: Dict[str, Any]) -> Optional[misirlou.Match]:
    """
    Creates a misirlou match and attempts to invite all required players

    :param misirlou_match: a dictionary containing misirlou api data
    :return: the id of the match that has just been created
    """
    for k, v in bot.tournament_matches.items():
        if misirlou_match["id"] == v.id_:
            # Already exists
            return None
    # Dict -> object
    match = misirlou.Match.json_factory(
        misirlou_match,
        password=general.random_secure_string(8).replace(" ", "_")
    )
    bancho_match_id = await bot.bancho_api_client.create_match(
        name=f"{match.tournament.abbreviation}: "
             f"({match.team_a.name}) vs ({match.team_b.name})",
        password=match.password,
        slots=match.tournament.team_size * 2 + 1,  # 1 extra slot for human ref, just in case
        game_mode=match.tournament.game_mode,
        beatmap=BanchoApiBeatmap(
            2116202,
            "06b536749d5a59536983854be90504ee",
            misirlou_match['tournament']['name']
        ),  # TODO: change
    )
    match.bancho_match_id = bancho_match_id
    await bot.bancho_api_client.edit_match(
        match.bancho_match_id,
        team_type=TeamType.TEAM_VS,
        scoring_type=ScoringType.SCORE_V2,
    )
    await bot.bancho_api_client.freeze(match.bancho_match_id, enable=True)

    # Send invites
    for member in match.team_a.members + match.team_b.members:
        if await bot.bancho_api_client.is_online(member, game_only=True):
            bot.send_message(
                f"Your match on tournament {match.tournament.name} is ready! "
                f"\"[osump://{match.bancho_match_id}/{match.password} Click here to join it]\"",
                member,
            )
    bot.tournament_matches[bancho_match_id] = match
    return match


@bot.command("t create")
@plugins.base.protected(Privileges.USER_TOURNAMENT_STAFF)
@plugins.base.base
async def create() -> str:
    matches = await bot.misirlou_api_client.get_matches()
    r = [
        x for x in
        await asyncio.gather(*(create_misirlou_match(x) for x in matches))
        if x is not None
    ]
    return f"{len(r)} pending match{' has' if len(r) == 1 else 'es have'} " \
           f"been created (ids: {[x.bancho_match_id for x in r]})."


@bot.client.on("msg:match_user_joined")
@resolve_tournament_only
async def match_user_joined(match: Dict[str, Any], tournament_match: misirlou.Match, user: Dict[str, Any], **_) -> None:
    # Determine the slot of whoever joined the match
    new_user = user
    new_slot = None
    new_slot_idx = None
    for i, slot in enumerate(match["slots"]):
        if slot["user"]["api_identifier"] == new_user["api_identifier"]:
            new_slot = slot
            new_slot_idx = i
            break
    assert new_slot is not None and new_slot_idx is not None

    # Check if they are a player
    the_team = tournament_match.get_user_team(new_user["user_id"])
    if the_team is not None:
        # Team player, move them in the right spot

        # TODO: If there's another client from the same user, kick the old one

        if len(the_team.members_in_match) >= tournament_match.tournament.team_size:
            # Too many players in this team, this player is not needed. Kick them.
            await bot.bancho_api_client.match_kick(tournament_match.bancho_match_id, new_user["api_identifier"])
            bot.send_message(
                "Your team is full, please ask one of your teammates "
                "to leave the match if you want to play instead.",
                new_user["api_identifier"]
            )
            return

        # Ok, move them to the right free slot for this team
        # Team A gets the first half of the slots, Team B gets the second half
        first_slot = tournament_match.tournament.team_size * (0 if the_team.enum == MisirlouTeam.A else 1)
        new_new_slot_idx = None
        for s_i, the_slot in enumerate(match["slots"][first_slot:first_slot + tournament_match.tournament.team_size]):
            if SlotStatus(the_slot["status"]) == SlotStatus.OPEN or (
                the_slot["user"] is not None and the_slot["user"]["api_identifier"] == new_user["api_identifier"]
            ):
                new_new_slot_idx = first_slot + s_i
                break
        # A slot must exist!
        assert new_new_slot_idx is not None
        # If different slot, move
        if new_slot_idx != new_new_slot_idx:
            await bot.bancho_api_client.match_move_user(
                tournament_match.bancho_match_id, new_user["api_identifier"], new_new_slot_idx
            )
        # Also set the team (always)
        await bot.bancho_api_client.set_team(
            tournament_match.bancho_match_id, new_user["api_identifier"], the_team.enum.bancho_team
        )

        # Update state
        the_team.members_in_match.add(new_user["user_id"])
        tournament_match.usernames[new_user["user_id"]] = new_user["username"]

        # Greet the user with a notification
        await bot.bancho_api_client.alert(
            new_user["api_identifier"],
            f"@@@ {tournament_match.tournament.name} @@@\n\n"
            "Welcome to your tournament match!\nThe match will begin as soon as all the players show up. "
            "Please be ready to start playing and don't go afk. The match is managed by an automated bot. "
            "If you need any kind of assistance you can call a human referee with the command '!t humanref'.\n\n"
            "Have fun and good luck!"
        )

        # Notify the bot if the teams are full
        if len(the_team.members_in_match) == \
                len(tournament_match.team_enum_to_team(the_team.enum.other).members_in_match) == \
                tournament_match.tournament.team_size:
            bot.client.trigger("tournament_match_full", match_id=tournament_match.bancho_match_id)
        return

    # Not a tournament player, allow only refs
    if not Privileges(new_user["privileges"]).has(Privileges.USER_TOURNAMENT_STAFF):
        # Who is this person? Who called them?
        await bot.bancho_api_client.match_kick(tournament_match.bancho_match_id, new_user["api_identifier"])
        await bot.bancho_api_client.alert(
            new_user["api_identifier"],
            "This is a tournament match and you are not allowed to be in there."
        )
        return

    # Tournament staff, move them in the last free slot so they don't mess up
    # with the tournament client view
    last_free_slot_idx = None
    for slot_idx, slot in reversed(list(enumerate(match["slots"]))):
        if SlotStatus(slot["status"]).has(SlotStatus.OPEN):
            last_free_slot_idx = slot_idx
            break
    if last_free_slot_idx is None:
        # No slot? don't move them, they won't hurt anyone
        logging.warning("No more free slots available in the tournament match?")
    else:
        await bot.bancho_api_client.match_move_user(
            tournament_match.bancho_match_id,
            new_user["api_identifier"],
            last_free_slot_idx,
        )


@bot.client.on("tournament_first_rolled")
@plugins.base.wrap_response_multiplayer
async def tournament_first_rolled(match_id: int) -> str:
    match = bot.tournament_matches[match_id]
    other_team = match.team_a if match.team_a.roll is None else match.team_b
    return f"{match.captain_or_team_name(other_team)}, please roll."


@bot.client.on("tournament_both_rolled")
async def tournament_both_rolled(match_id: int) -> None:
    match = bot.tournament_matches[match_id]
    for msg in (
        f"{match.captain_or_team_name(match.roll_winner)} won the roll!",
        "Please pick your first ban. Here's the pool:"
    ):
        bot.send_message(msg, match.chat_channel_name)
    _send_map_pool(match)
    _send_ask_beatmap(match, match.roll_winner, operation="ban", confirmation=True)


def _send_map_pool(match: misirlou.Match):
    for k, group in match.tournament.pool.items():
        for i, beatmap in enumerate(group):
            bot.send_message(f"► {beatmap.mods.tournament_str}{i + 1}: {beatmap.name}", match.chat_channel_name)


def _send_ask_beatmap(
    match: misirlou.Match, picking_team: misirlou.Team, operation: str, confirmation: bool
) -> None:
    who = match.captain_or_team_members(picking_team)
    if not picking_team.captain_in_match:
        who += ", any of you"
    bot.send_message(
        f"{who}, please type one beatmap you want to {operation} (eg: NM1, HD2, etc). "
        f"I will{' not ' if not confirmation else ' '}ask for confirmation.",
        match.chat_channel_name
    )


def tournament_regex_pre(*, recipient: Dict[str, Any], pm: bool, **_) -> bool:
    """
    Regex pre that returns True only if the message is sent in a
    registered tournament match chat channel.

    :return: True if the message is sent in a tournament match chat channel
    """
    return \
        not pm and recipient["name"].startswith("#multi_") \
        and int(recipient["name"].split("_")[1]) in bot.tournament_matches.keys()


@bot.command(re.compile(r"(NM|HD|HR|DT|FM)+(\d)", re.IGNORECASE), pre=tournament_regex_pre)
async def on_map(**_) -> str:
    logging.debug("ON MAP XDD")
    return "OWO"


@bot.client.on("tournament_match_full")
async def tournament_match_full(match_id: int) -> None:
    match = bot.tournament_matches[match_id]
    for msg in (
        f"Welcome to your {match.tournament.name} tournament match! Please be ready to start playing and don't go afk.",
        f"I am the referree bot and I will guide you through your match",
        f"If you need any assistance with the match, you can call a human referree with the command '!t humanref'",
        "All players are present, we can now roll to determine who will pick their first ban.",
    ):
        bot.send_message(msg, match.chat_channel_name)
    msg = ""
    for i, team in enumerate((match.team_a, match.team_b)):
        if team.captain_in_match:
            msg += f"{match.usernames[team.captain]}"
            if not match.tournament.is_solo:
                msg += f" ({team.name}'s captain)"
        else:
            msg += ", ".join(match.usernames[x] for x in team.members_in_match)
            msg += f" ({team.name}'s members)"
        if i == 0:
            msg += " - "
    msg += ", any of you, please roll with the !roll command."
    bot.send_message(msg, match.chat_channel_name)
