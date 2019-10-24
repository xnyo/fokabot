import logging
from typing import Optional, Dict, Any, List

import aiohttp

from constants import beatconnect


class BeatconnectAPIError(Exception):
    pass


class BeatconnectFatalError(BeatconnectAPIError):
    pass


class BeatconnectAPIClient:
    logger = logging.getLogger("beatconnect_api")

    def __init__(self, api_token: str, base_url: str = "https://beatconnect.io"):
        self.base_url = f"{base_url.rstrip('/')}/api"
        self.api_token = api_token

    async def request(self, handler: str, params: Optional[Dict[str, Any]] = None):
        # Beatconnect uses https://beatconnect.io/api/<something>/?params
        handler = f"{handler.lstrip('/').rstrip('/')}/"
        async with aiohttp.ClientSession(headers={"Token": self.api_token}) as session:
            try:
                url = f"{self.base_url}/{handler}"
                log = f"[GET] {url} <{params}>"
                self.logger.debug(log)
                async with session.get(url, params=params) as response:
                    if response.status != 200:
                        text = await response.text()
                        raise BeatconnectAPIError(f"Bad response ({response.status}): {text}")
                    json_response = await response.json()
                    self.logger.debug(f"{log} -> {json_response}")
                    return json_response
            except (aiohttp.ServerConnectionError, aiohttp.ClientError, ValueError) as e:
                raise BeatconnectFatalError(e)

    async def get_beatmap(
        self,
        query: str,
        *,
        status: beatconnect.Status = beatconnect.Status.ALL,
        mode: beatconnect.Mode = beatconnect.Mode.ALL,
        page: int = 0,
        diff_from: float = 0,
        diff_to: float = 10
    ) -> List[Dict[str, Any]]:
        diff = f"{diff_from}-{diff_to}"
        r = await self.request("search/", {
            "s": status.value,
            "m": mode.value,
            "q": query,
            "p": page,
            "diff_range": diff
        })
        if r is None or "beatmaps" not in r:
            raise BeatconnectAPIError("No 'beatmaps' field in response.")
        return r["beatmaps"]

    async def get_beatmap_by_set_id(self, beatmap_set_id: int, **kwargs) -> Optional[Dict[str, Any]]:
        r = await self.get_beatmap(str(beatmap_set_id), **kwargs)
        if not r:
            return None
        return r[0]

    async def get_download_link(self, beatmap_set_id: int) -> Optional[str]:
        beatconnect_response = await self.get_beatmap_by_set_id(beatmap_set_id)
        if beatconnect_response is None:
            return None
        unique_id = beatconnect_response["unique_id"]
        return f"https://beatconnect.io/b/{beatmap_set_id}/{unique_id}"
