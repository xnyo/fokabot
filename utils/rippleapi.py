import logging
import ujson
from datetime import datetime
from typing import Optional, Dict, Any, Callable, List

import aiohttp
import async_timeout
from abc import ABC, abstractmethod
from enum import IntEnum, auto

from constants.game_modes import GameMode


class BanchoApiBeatmap:
    def __init__(self, id_: Optional[int] = None, md5: Optional[str] = None, song_name: Optional[str] = None):
        self.id_ = id_
        self.md5 = md5
        self.song_name = song_name

    def __dict__(self) -> Dict[str, Any]:
        return {
            "id": self.id_,
            "md5": self.md5,
            "song_name": self.song_name
        }


class RippleApiError(Exception):
    pass


class RippleApiResponseError(RippleApiError):
    CODE = None

    def __init__(self, data: Dict[Any, Any]):
        """
        A generic ripple api caused by a non 2xx response code

        :param data: the json response data
        """
        self.data = data

    @classmethod
    def factory(cls, data: Dict[Any, Any]) -> Exception:
        """
        Creates a RippleApiResponseError subclass based on the "code"
        of the request

        :param data: api json response dict
        :return: an Exception (that should be raised). Can be a RippleApiResponseError if there's no more specific
        exception, otherwise it's always RippleApiResponseError subclass.
        """
        response_code = data.get("code", None)
        return (
            cls if response_code is None
            else next((x for x in cls.__subclasses__() if x.CODE == response_code), cls)
        )(data)


class InvalidArgumentsError(RippleApiResponseError):
    CODE = 403


class NotFoundError(RippleApiResponseError):
    CODE = 404


class RippleApiFatalError(RippleApiError):
    """
    A fatal error. Happens when it's not even possible to
    get a valid json response from the api (eg: networking issue,
    server-side issue)
    """
    pass


class RippleApiBaseClient(ABC):
    logger = logging.getLogger("abstract_api")

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
        # self._session: aiohttp.ClientSession = None

    @property
    def headers(self) -> Dict[str, Any]:
        return {"User-Agent": self.user_agent} if self.user_agent is not None else {}

    @staticmethod
    def bind_error_code(status_code: int, return_value: Any) -> Callable:
        """
        Returns a specific value when a status code is returned.
        Note that this will only work with error response codes.

        :param status_code: the status code
        :param return_value: the return value
        :return:
        """
        def decorator(f: Callable) -> Callable:
            async def wrapper(*args, **kwargs):
                try:
                    return await f(*args, **kwargs)
                except RippleApiResponseError as e:
                    if e.data["code"] == status_code:
                        return return_value
                    raise e
            return wrapper
        return decorator

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
        :raises RippleApiError subclass: if there was a legal response from the server,
                                         but the status code code was an error
        :raises RippleApiError: if there was a legal response from the server, but the status code code was an error
                                and there's no specific Exception bound to that error
        :raises RippleApiFatalError: if the request wasn't processed correctly (network error, server error, json
                                     decode error, etc)
        """
        # Default parameter
        if data is None:
            data = {}

        # Reuse the same session within the same client
        # if self._session is None:
        #     self._session = aiohttp.ClientSession(headers=self.headers)
        async with aiohttp.ClientSession(headers=self.headers) as session:
            with async_timeout.timeout(self.timeout):
                # Start with no json data and no GET parameters
                json_data = None
                params = None

                # TODO: factory method.
                #  (can we call it "factory" even if we're returning
                #  funcions and not classes? Gang of Fur cit)
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
                        # self.logger.debug(response.headers)
                        result = await response.json(loads=ujson.loads)
                except (aiohttp.ServerConnectionError, aiohttp.ClientError, ValueError) as e:
                    raise RippleApiFatalError(e)

                # Make sure the response was valid
                if result.get("code", None) != 200:
                    raise RippleApiResponseError.factory(result)

                return result

    @property
    @abstractmethod
    def api_link(self) -> str:
        raise NotImplementedError()

    @staticmethod
    def datetime_to_rfc3339(d: datetime) -> str:
        return d.strftime("%Y-%m-%dT%H:%M:%S+00:00")

    @staticmethod
    def remove_none(d):
        d = {k: v for k, v in d.items() if v is not None}
        for k, v in d.items():
            if type(v) is dict:
                d[k] = RippleApiBaseClient.remove_none(v)
        return d


class BanchoClientType(IntEnum):
    """
    Bancho API client types, according to delta's API
    """
    OSU = 0
    IRC = auto()


class BanchoApiClient(RippleApiBaseClient):
    logger = logging.getLogger("bancho_api")

    @property
    def api_link(self) -> str:
        return f"{self.base.rstrip('/')}/api/v2"

    async def mass_alert(self, message: str) -> None:
        """
        Sends a mass ServerAnnounce packet to all connected user on bancho

        :param message: the message
        :return:
        """
        await self._request("system/mass_alert", "POST", {
            "message": message
        })

    async def alert(self, api_identifier: str, message: str) -> None:
        """
        Sends a ServerAnnounce packet to a specified user connected to bancho

        :param api_identifier: api identifier of the user. Must be a game client or the api will return an error.
        :param message: the message
        :return:
        """
        await self._request(f"clients/{api_identifier}/alert", "POST", {
            "message": message
        })

    async def get_clients(self, user_id: int) -> Dict[Any, Any]:
        """
        Returns all clients that belong to that user as a list of dictionaries

        :param user_id: id of the user
        :return: list of dictionaries containing the clients that belong to that user.
                 empty list if there are no connected clients for that user
        """
        response = await self._request(f"clients/{user_id}")
        return response.get("clients", [])

    @RippleApiBaseClient.bind_error_code(400, None)
    async def get_client(self, user_id: int, game_only: bool = False) -> Optional[Dict[Any, Any]]:
        """
        Returns a single client (the first one) for the selected user

        :param user_id: id of the user
        :param game_only: id True, get only the first game client and ignore all irc clients
        :return: dictionary, or None if there's no such client for the provided user
        """
        clients = await self.get_clients(user_id)
        if not clients:
            return None
        for client in clients:
            if game_only and client["type"] == BanchoClientType.OSU or not game_only:
                return client
        return None

    async def moderated(self, channel: str, moderated: bool) -> None:
        """
        Puts a channel in moderated mode or turns moderated mode off

        :param channel: channel name. Can start with or without #
        :param moderated: True/False
        :return:
        """
        if channel.startswith("#"):
            channel = channel.lstrip("#")
        await self._request(f"chat_channels/{channel}", "POST", {"moderated": moderated})

    async def kick(self, api_identifier: str) -> None:
        """
        Kicks a user from bancho

        :param api_identifier: the api identifier of the user. Must belong to a game client.
        :return:
        """
        await self._request(f"clients/{api_identifier}/kick", "POST")

    async def rtx(self, api_identifier: str, message: str) -> None:
        """
        RTXes someone

        :param api_identifier: api identifier of the user. Must belong to a game client.
        :param message: message to display
        :return:
        """
        await self._request(f"clients/{api_identifier}/rtx", "POST", {"message": message})

    async def system_info(self) -> Dict[Any, Any]:
        """
        Returns some information about the currently running bancho server

        :return:
        """
        return await self._request("system", "GET")

    @RippleApiBaseClient.bind_error_code(409, False)
    async def graceful_shutdown(self) -> bool:
        """
        Gracefully shuts down bancho

        :return: True if the request was accepted,
                 False if the server is already restarting.
        """
        await self._request("system/graceful_shutdown", "POST")
        return True

    @RippleApiBaseClient.bind_error_code(409, False)
    async def cancel_graceful_shutdown(self) -> bool:
        """
        Cancels a graceful shutdown, if it exists.

        :return: True if the request was accepted,
                 False if the server is not restarting.
        """
        await self._request("system/graceful_shutdown", "DELETE")
        return True

    async def create_match(
        self, name: str, password: Optional[str] = None, slots: int = None,
        game_mode: GameMode = None, seed: int = None, beatmap: BanchoApiBeatmap = None
    ) -> int:
        if beatmap is not None:
            beatmap = beatmap.__dict__()
        d = self.remove_none({
            "name": name,
            "password": password,
            "slots": slots,
            "game_mode": game_mode,
            "seed": seed,
            "beatmap": beatmap
        })
        if d.get("game_mode", None) is not None:
            d["game_mode"] = int(d["game_mode"])
        response = await self._request("multiplayer", "POST", d)
        return response.get("match_id")

    async def join_match(self, api_identifier: str, match_id: int, password: Optional[str]) -> None:
        await self._request(f"clients/{api_identifier}/join_match", "POST", self.remove_none({
            "match_id": match_id,
            "password": password
        }))

    async def get_all_channels(self) -> List[Dict[str, Any]]:
        response = await self._request("chat_channels", "GET", {
            "filter": "all"
        })
        return response.get("channels")


class RippleApiClient(RippleApiBaseClient):
    logger = logging.getLogger("ripple_api")

    @property
    def api_link(self) -> str:
        return f"{self.base.rstrip('/')}/api/v1"

    @RippleApiBaseClient.bind_error_code(404, None)
    async def what_id(self, username: str) -> Optional[int]:
        """
        Returns the id of a user from their username (normal or ircified).
        Returns None if there's no such user

        :param username: username, either normal or ircified
        :return: user id or None
        """
        response = await self._request("users/whatid", "GET", {
            "name": username
        })
        return response.get("id", None)

    async def get_user(
        self, username: Optional[str] = None, user_id: Optional[int] = None
    ) -> Optional[List[Dict[str, Any]]]:
        has_username = username is not None
        has_user_id = user_id is not None
        if has_user_id == has_username:
            raise ValueError("Either username or user_id must be provided")
        if has_username:
            params = {"nname": username}
        else:
            params = {"iid": user_id}
        response = await self._request("users", "GET", params)
        users = response.get("users", None)
        if not users:
            return None
        return users

    async def set_allowed(self, user_id: int, new_allowed: int):
        return await self._request("users/manage/set_allowed", "POST", {
            "user_id": user_id,
            "allowed": new_allowed
        })

    async def edit_user(
        self, user_id: int, *,
        username: Optional[str] = None, username_aka: Optional[str] = None,
        country: Optional[str] = None, reset_userpage: Optional[bool] = None,
        silence_reason: Optional[str] = None, silence_end: Optional[datetime] = None
    ) -> Dict[str, Any]:
        data = {"id": user_id}
        for k, v in zip(
            ("username", "username_aka", "country", "reset_userpage"),
            (username, username_aka, country, reset_userpage)
        ):
            if v is not None:
                data[k] = v
        if silence_reason is not None or silence_end is not None:
            data["silence_info"] = {}
        if silence_reason is not None:
            data["silence_info"]["reason"] = silence_reason
        if silence_end is not None:
            data["silence_info"]["end"] = RippleApiClient.datetime_to_rfc3339(silence_end)
        return await self._request("users/edit", "POST", data)

    async def _scores(
        self,
        sub_url: str,
        user_id: Optional[int] = None,
        username: Optional[str] = None,
        game_mode: Optional[GameMode] = None
    ) -> List[Dict[str, Any]]:
        if bool(user_id is None) == bool(username is None):
            raise ValueError("You must provide either user_id or username")
        d = {k: v for k, v in {"id": user_id, "name": username, "mode": int(game_mode) if game_mode is not None else None}.items() if v is not None}
        r = await self._request(f"users/scores/{sub_url}", "GET", d)
        scores = r.get("scores", [])
        if scores is None:
            return []
        return scores

    async def recent_scores(
        self,
        user_id: Optional[int] = None,
        username: Optional[str] = None,
        game_mode: Optional[GameMode] = None
    ) -> List[Dict[str, Any]]:
        return await self._scores("recent", user_id, username, game_mode)

    async def best_scores(
        self,
        user_id: Optional[int] = None,
        username: Optional[str] = None,
        game_mode: Optional[GameMode] = None
    ) -> List[Dict[str, Any]]:
        return await self._scores("best", user_id, username, game_mode)
