import json
import logging
from typing import Dict, Any, List, Union, Optional

import ujson
import aiohttp
import async_timeout

from constants.game_modes import GameMode
from constants.mods import Mod


class LetsApiError(Exception):
    pass


class FatalLetsApiError(LetsApiError):
    pass


class LetsPPResponse:
    def __init__(self, **kwargs):
        self.song_name: str = kwargs["song_name"]
        self._pp: Union[List[float], float] = kwargs["pp"]
        self.length: int = kwargs["length"]
        self.stars: float = kwargs["stars"]
        self.ar: float = kwargs["ar"]
        self.bpm: int = kwargs["bpm"]
        self.mods: Mod = kwargs["mods"]
        self.accuracy: Optional[float] = kwargs["accuracy"]
        self.game_mode: GameMode = GameMode(kwargs["game_mode"])

    @property
    def has_multiple_pp(self) -> bool:
        return type(self._pp) is list

    @property
    def pp(self) -> float:
        if self.has_multiple_pp:
            raise ValueError("This response has multiple PP. Please use pp_100, pp_99, pp_98 or pp_95.")
        return self._pp

    @property
    def pp_100(self) -> float:
        return self._pp[0] if self.has_multiple_pp else self._pp

    @property
    def pp_99(self) -> float:
        return self._pp[1] if self.has_multiple_pp else None

    @property
    def pp_98(self) -> float:
        return self._pp[2] if self.has_multiple_pp else None

    @property
    def pp_95(self) -> float:
        return self._pp[3] if self.has_multiple_pp else None

    # @property
    # def primary_game_mode(self) -> GameMode:
    #    return next((GameMode(i) for v, i in enumerate(self._pp) if v is not None and v > 0), GameMode.STANDARD)

    @property
    def modded_ar(self) -> float:
        if self.mods & Mod.EASY:
            return max(0.0, self.ar / 2)
        if self.mods & Mod.HARD_ROCK:
            return min(10.0, self.ar * 1.4)
        return self.ar

    def __str__(self) -> str:
        message = f"{self.song_name}"
        message += f" <{str(self.game_mode)}>"
        message += f"+{str(self.mods)}" if self.mods != Mod.NO_MOD else ""
        message += "  "
        if self.has_multiple_pp:
            message += " | ".join(f"{perc}%: {x:.2f}pp" for perc, x in zip((100, 99, 98, 95), self._pp))
        else:
            message += f"{self.accuracy:.2f}%: {self.pp:.2f}pp"
        original_ar = self.ar
        mod_ar = self.modded_ar
        message += \
            f" | ♪ {self.bpm}" \
            f" | AR {self.ar}{f' ({mod_ar:.2f})' if mod_ar != original_ar else ''}" \
            f" | ★ {self.stars:.2f}"
        return message


class LetsApiClient:
    logger = logging.getLogger("lets_api")

    def __init__(self, base: str, timeout: int = 5):
        self.base = base.rstrip("/")
        self.timeout = timeout

    async def _request(self, url: str, params: Dict[str, Any]) -> Dict[Any, Any]:
        url = url.lstrip("/")
        async with aiohttp.ClientSession() as session:
            with async_timeout.timeout(self.timeout):
                async with session.get(f"{self.base}/{url}", params=params) as response:
                    try:
                        self.logger.debug(f"LETS request: GET {self.base}/{url} [{params}]")
                        return await response.json(loads=ujson.loads)
                    except (ValueError, json.JSONDecodeError):
                        raise FatalLetsApiError(response)

    async def get_pp(
        self, beatmap_id: int,
        game_mode: GameMode = GameMode.STANDARD,
        mods: Mod = Mod.NO_MOD,
        accuracy: float = None
    ) -> LetsPPResponse:
        params = {"b": beatmap_id, "m": int(mods), "g": int(game_mode)}
        if accuracy is not None:
            params["a"] = str(accuracy)
        r = await self._request("v1/pp", params)
        status = r.get("status")
        if status != 200:
            exc_info = r["message"] if "message" in r else r
            self.logger.error(f"LETS api error: {exc_info}")
            raise LetsApiError(exc_info)
        self.logger.debug(r)
        return LetsPPResponse(**r, mods=mods, accuracy=accuracy)

