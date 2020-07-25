import asyncio
from typing import Dict, Any, Optional

from constants.privileges import Privileges
from constants.scoring_types import ScoringType
from constants.team_types import TeamType
from singletons.bot import Bot
from utils import misirlou, general
from utils.rippleapi import BanchoApiBeatmap
import plugins.base

bot = Bot()


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
