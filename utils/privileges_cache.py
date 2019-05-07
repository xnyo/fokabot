import logging
import time
from typing import Dict, Optional, TypeVar, Any

from constants.privileges import Privileges
from utils.rippleapi import RippleApiClient
from utils import general


class CachedPrivileges:
    def __init__(self, privileges: Privileges, expiration_time: int = 1800):
        self.privileges = privileges
        self.add_time = int(time.time())
        self.expiration_time = expiration_time

    @classmethod
    def api_user_factory(cls, user: Dict[str, Any]) -> "CachedPrivilegesT":
        return cls(Privileges(user["privileges"]))

    @property
    def is_expired(self) -> bool:
        return int(time.time()) - self.add_time > self.expiration_time

    def __str__(self) -> str:
        return f"<{self.__class__.__name__}> " + \
               (
                   ", ".join(
                       f"{k}={getattr(self, k)}"
                       for k in dir(self)
                       if not k.startswith("__") and not callable(getattr(self, k))
                   )
               )


CachedPrivilegesT = TypeVar("CachedPrivilegesT", bound=CachedPrivileges)


class PrivilegesCache:
    logger = logging.getLogger("privileges_cache")

    def __init__(self, ripple_api_client: RippleApiClient):
        self._data: Dict[str, CachedPrivileges] = {}
        self._ripple_api_client: RippleApiClient = ripple_api_client

    async def get(self, username: str) -> Optional[Privileges]:
        username = general.safefify_username(username)
        await self.cache_privileges(username)
        cached_privileges = self._data.get(username, None)
        self.logger.debug(f"Cached privileges for user {username}: {cached_privileges}")
        if cached_privileges is None:
            return None
        return cached_privileges.privileges

    async def cache_privileges(self, username: str, force: bool = False):
        username = general.safefify_username(username)
        if not force:
            cached_privileges = self._data.get(username, None)
            if cached_privileges is not None and not cached_privileges.is_expired:
                self.logger.debug(f"Privileges for user {username} are in cache and haven't expired yet.")
                return
        self.logger.debug(f"Caching privileges for user {username}")
        users = await self._ripple_api_client.get_user(username)
        if not users:
            self.logger.error(f"Cannot cache privileged for user {users}! The user does not exist.")
            return
        self._data[username] = CachedPrivileges.api_user_factory(users[0])

    def purge(self) -> None:
        self.logger.debug(f"Deleting expired cached privileges")
        to_delete = []
        for k, v in self._data.items():
            if v.is_expired:
                to_delete.append(k)
        for k in to_delete:
            del self._data[k]
        self.logger.debug(f"Deleted {len(to_delete)} cached privileges ({to_delete})")

    def __len__(self) -> int:
        return len(self._data)
