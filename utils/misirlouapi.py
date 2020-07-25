import logging
from typing import Dict, Any, List

from utils.rippleapi import RippleApiBaseClient


class MisirlouApiClient(RippleApiBaseClient):
    logger = logging.getLogger("misirlou_api")

    def __init__(self, token: str, base: str = "https://tourn.ripple.moe", user_agent: str = "fokabot", timeout: int = 5):
        super(MisirlouApiClient, self).__init__(
            token=token, base=base, user_agent=user_agent, timeout=timeout,
            check_status=False, auth_header="Authorization"
        )

    @property
    def api_link(self) -> str:
        return f"{self.base.rstrip('/')}/api/fokabot"

    async def get_matches(self) -> List[Dict[str, Any]]:
        return await self._request("matches")
