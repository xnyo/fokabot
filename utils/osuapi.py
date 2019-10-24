import logging
from typing import Optional, Dict, Any

import aiohttp


class OsuAPIError(Exception):
    pass


class OsuAPIFatalError(OsuAPIError):
    pass


class OsuAPIClient:
    """
    A very basic osu! API v1 client with very few handlers supported
    """
    logger = logging.getLogger("osu_api_v1")

    def __init__(self, api_token: str):
        self.api_token = api_token

    async def request(self, handler, params: Optional[Dict[str, Any]] = None):
        if params is None:
            params = {}
        if "k" in params:
            del params["k"]
        params = {**params, **{"k": self.api_token}}
        async with aiohttp.ClientSession() as session:
            try:
                url = f"https://osu.ppy.sh/api/{handler}"
                self.logger.debug(f"[GET] {url} <{params}>")
                async with session.get(url, params=params) as response:
                    if response.status != 200:
                        text = await response.text()
                        raise OsuAPIError(f"Bad response ({response.status}): {text}")
                    return await response.json()
            except (aiohttp.ServerConnectionError, aiohttp.ClientError, ValueError) as e:
                raise OsuAPIFatalError(e)
