import logging
import ujson
from typing import Optional, Dict, Any

import aiohttp
import async_timeout
from abc import ABC, abstractmethod
from enum import IntEnum, auto


class RippleApiError(Exception):
    pass


class RippleApiResponseError(RippleApiError):
    def __init__(self, data):
        self.data = data


class RippleApiFatalError(RippleApiError):
    pass


class RippleApiBaseClient(ABC):
    logger = logging.getLogger("abapiclient")

    def __init__(
        self, token: Optional[str] = None, base: str = "https://ripple.moe",
        user_agent: str = "fokabot", timeout: int = 5
    ):
        """
        Initializes a new BanchoAPiClient

        :param token: token
        :param base: api base
        :param user_agent: user agent
        :param timeout: time to wait in seconds before giving up requests
        """
        self.token = token
        self.base = base
        self.user_agent = user_agent
        self.timeout = timeout
        self.user_id = 0
        self.privileges = 0
        self.user_privileges = 0

    @property
    def headers(self) -> Dict[str, Any]:
        return {"User-Agent": self.user_agent} if self.user_agent is not None else {}

    async def _request(
        self, handler: str, method: str = "GET", data: Optional[Dict[Any, Any]] = None
    ) -> Dict[Any, Any]:
        """
        Sends a request to the ripple api

        :param handler: api handler (eg: users)
        :param method: method, can be "GET"/"POST" and so on
        :param data: data to send. Will be sent as GET parameters if method is `GET`,
                     or json encoded and sent as POST body if method is `POST`.
                     most of the time, passing a `dict` is fine, however, if you need
                     to repeat multiple times the same parameter (eg: /users&ids=999&ids=1000,
                     to get user info about multiple users with 1 request), you must
                     use a `multidict.MultiDict` instead.
        :return: full decoded json body
        """
        # Default parameter
        if data is None:
            data = {}

        # TODO: Single session
        async with aiohttp.ClientSession(headers=self.headers) as session:
            with async_timeout.timeout(self.timeout):
                # Start with no json data and no GET parameters
                json_data = None
                params = None

                if method == "POST":
                    # Use POST and json body
                    f = session.post
                    json_data = data
                elif method == "GET":
                    # Use GET and querystring
                    f = session.get
                    params = data
                elif method == "DELETE":
                    f = session.delete
                    json_data = data
                else:
                    raise ValueError("Unsupported method")

                # Different authorization header based on our authentication method
                # (oauth or normal token)
                headers = {"X-Ripple-Token": self.token}

                # Send the API request
                try:
                    url = f"{self.api_link}/{handler}"
                    self.logger.debug(f"[{method}] {url} <{params}> <{json_data}>")
                    async with f(
                        url,
                        headers=headers,
                        json=json_data,
                        params=params
                    ) as response:
                        # Decode the response and return it
                        # self.logger.debug(await response.text())
                        result = await response.json(loads=ujson.loads)
                except (aiohttp.ServerConnectionError, aiohttp.ClientError, ValueError) as e:
                    raise RippleApiFatalError(e)

                # Make sure the response was valid
                if result.get("code", None) != 200:
                    raise RippleApiResponseError(result)

                return result

    @property
    @abstractmethod
    def api_link(self) -> str:
        raise NotImplementedError()


class BanchoClientType(IntEnum):
    OSU = 0
    IRC = auto()


class BanchoApiClient(RippleApiBaseClient):
    @property
    def api_link(self) -> str:
        return f"{self.base.rstrip('/')}/api/v2"

    async def mass_alert(self, message: str) -> Dict[Any, Any]:
        return await self._request("system/mass_alert", "POST", {
            "message": message
        })

    async def alert(self, api_identifier: str, message: str) -> Dict[Any, Any]:
        return await self._request(f"clients/{api_identifier}/alert", "POST", {
            "message": message
        })

    async def get_clients(self, user_id: int, game_only: bool = False) -> Dict[Any, Any]:
        response = await self._request(f"clients/{user_id}")
        return response.get("clients", [])

    async def get_client(self, user_id: int, game_only: bool = False) -> Optional[Dict[Any, Any]]:
        try:
            clients = await self.get_clients(user_id)
            if not clients:
                return None
            for client in clients:
                if game_only and client["type"] == BanchoClientType.OSU or not game_only:
                    return client
            return None
        except RippleApiResponseError as e:
            if e.data["code"] == 400:
                self.logger.debug(e)
                return None

    async def moderated(self, channel: str, moderated: bool) -> Optional[Dict[Any, Any]]:
        if channel.startswith("#"):
            channel = channel.lstrip("#")
        return await self._request(f"chat_channels/{channel}", "POST", {"moderated": moderated})

    async def kick(self, api_identifier: str) -> bool:
        try:
            await self._request(f"clients/{api_identifier}/kick", "POST")
        except RippleApiResponseError as e:
            if e.data["code"] == 400:
                return False
            raise e
        return True

    async def rtx(self, api_identifier: str, message: str) -> bool:
        try:
            await self._request(f"clients/{api_identifier}/rtx", "POST", {"message": message})
        except RippleApiResponseError as e:
            if e.data["code"] == 400:
                return False
            raise e
        return True


class RippleApiClient(RippleApiBaseClient):
    @property
    def api_link(self) -> str:
        return f"{self.base.rstrip('/')}/api/v1"

    async def what_id(self, username: str) -> Optional[int]:
        try:
            response = await self._request("users/whatid", "GET", {
                "name": username
            })
        except RippleApiError:
            return None
        return response.get("id", None)
