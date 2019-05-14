import logging
import datetime
from typing import Dict, Optional, TypeVar, Any

from constants.privileges import Privileges
from utils.rippleapi import RippleApiClient
from utils.cache import CacheElement, CacheStorage, SafeUsernamesDict


class CachedPrivileges(CacheElement):
    def __init__(self, privileges: Privileges, expiration_delta: datetime.timedelta = datetime.timedelta(minutes=30)):
        super(CachedPrivileges, self).__init__(expiration_delta=expiration_delta)
        self.privileges = privileges

    @classmethod
    def api_user_factory(cls, user: Dict[str, Any]) -> "CachedPrivilegesT":
        return cls(Privileges(user["privileges"]))

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


class PrivilegesCache(CacheStorage):
    logger = logging.getLogger("privileges_cache")

    def __init__(self, ripple_api_client: RippleApiClient):
        super(PrivilegesCache, self).__init__()
        self._data: SafeUsernamesDict[str, CachedPrivileges] = SafeUsernamesDict()
        self._ripple_api_client: RippleApiClient = ripple_api_client

    async def get(self, username: str) -> Optional[Privileges]:
        await self._cache_privileges(username)
        cached_privileges = self._data.get(username, None)
        self.logger.debug(f"Cached privileges for user {username}: {cached_privileges}")
        if cached_privileges is None:
            return None
        return cached_privileges.privileges

    async def _cache_privileges(self, username: str, force: bool = False):
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

    def __getitem__(self, item: int = None) -> None:
        raise RuntimeError(
            "This cache is async and does not support __getitem__ and __setitem__. "
            "Please use the get() coroutine instead."
        )

    def __setitem__(self, key: int, value: CachedPrivileges) -> None:
        self.__getitem__()
