from typing import Dict, Any

from constants.misirlou_teams import MisirlouTeam
from constants.privileges import Privileges
from constants.slot_statuses import SlotStatus
from singletons.bot import Bot
import plugins.tournament
from utils import misirlou

bot = Bot()


@bot.client.on("msg:match_user_joined")
@plugins.tournament.resolve_tournament_only
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
        plugins.tournament.logger.warning("No more free slots available in the tournament match?")
    else:
        await bot.bancho_api_client.match_move_user(
            tournament_match.bancho_match_id,
            new_user["api_identifier"],
            last_free_slot_idx,
        )


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
        msg += match.captain_or_team_members(team)
        if i == 0:
            msg += " - "
    msg += ", any of you, please roll with the !roll command."
    bot.send_message(msg, match.chat_channel_name)
