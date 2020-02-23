import datetime
import threading
from typing import Dict, Any, Optional

import logging

from collections import UserDict

from utils import general


class SafeUsernamesDict(UserDict):
    """
    A custom dictionary where keys are always converted to safe usernames
    """
    def __setitem__(self, key, value):
        self.data[general.safefify_username(key)] = value

    def __getitem__(self, item):
        return self.data[general.safefify_username(item)]

    def __contains__(self, item):
        return general.safefify_username(item) in self.data


class CacheElement:
    def __init__(self, expiration_delta: datetime.timedelta, add_time: Optional[datetime.datetime] = None):
        """
        Initializes a new cached element.
        It's recommended to subclass this object and call "super(...).__init__(...)"
        only after setting the instance values. This is because, after calling this
        constructor, all future "__setattr__" calls will update the cache refresh time
        and doing so for every attribute while constructing the object is not the best thing.

        :param expiration_delta: datetime.timedelta that explains for how long this object should be considered valid
        :param add_time: datetime.datetime of when the object should be considered as "created".
                         Leave to "None" to use datetime.datetime.now()
        """
        if add_time is None:
            add_time = datetime.datetime.now()
        self._cache__refresh_time = add_time
        self._cache__expiration_delta = expiration_delta

    @property
    def expiration_datetime(self) -> datetime.datetime:
        """
        Returns the datetime of when this cached element will expire

        :return:
        """
        return self._cache__refresh_time + self._cache__expiration_delta

    @property
    def is_expired(self) -> bool:
        """
        Whether this cached element is expired or not

        :return: True if it's expired, False otherwise
        """
        return datetime.datetime.now() > self.expiration_datetime

    def __setattr__(self, key: str, value: Any) -> None:
        """
        Sets an attribute and updates the cache refresh time.
        If the cache refresh time is not present (pre-initialization),
        it'll simply return the attribute value.

        :param key:
        :param value:
        :return:
        """
        # "hasattr" is needed so we can bulk set subclass attributes before calling "super()"
        # without updating _cache__refresh_time for each attribute
        if not key.startswith("_cache__") and hasattr(self, "_cache__refresh_time"):
            self._cache__refresh_time = datetime.datetime.now()
        super(CacheElement, self).__setattr__(key, value)


class CacheStorage:
    logger = logging.getLogger("general_cache_storage")

    def __init__(self):
        """
        Initializes a new CacheStorage object
        """
        self._data: Dict[Any, CacheElement] = {}
        self._lock: threading.Lock = threading.Lock()

    def purge(self) -> None:
        """
        Deletes all elements marked as "expired" from the storage

        :return:
        """
        with self._lock:
            self.logger.debug(f"Deleting expired cached elements")
            # Keep a counter to save some memory
            c = 0
            for k in (x for x, v in self._data.items() if v.is_expired):
                del self._data[k]
                c += 1
            self.logger.debug(f"Deleted {c} cached elements.")

    def __len__(self) -> int:
        """
        Returns the number of elements (both valid and expired) in the storage

        :return: number of total elements in the storage
        """
        with self._lock:
            return len(self._data)

    def __contains__(self, key: Any) -> bool:
        """
        Returns True if "key" is in the storage and is valid.

        :param key: cached element key
        :return: True if self[key] exists and has not expired yet, otherwise False
        """
        with self._lock:
            return key in self._data and not self._data[key].is_expired

    def __getitem__(self, item: Any) -> Optional[CacheElement]:
        """
        Returns an element from the storage.
        Raises KeyError is there's no such element.
        If the element has expired, it gets deleted and a KeyError is raised

        :param item: cached element key
        :return: the element
        :raises KeyError: if there's no element or it has expired
        """
        with self._lock:
            if self._data[item].is_expired:
                del self[item]
                # Recursively call __getitem__ to raise a KeyError
                return self[item]
            return self._data[item]

    def __setitem__(self, key: Any, value: CacheElement) -> None:
        """
        Sets an element in the storage

        :param key: cached element key
        :param value: cached element
        :return:
        """
        with self._lock:
            self._data[key] = value

    def __delitem__(self, key: Any) -> None:
        """
        Deletes an element.
        Does nothing if there's no element with such key

        :param key: cached element key
        :return:
        """
        with self._lock:
            try:
                del self._data[key]
            except KeyError:
                pass
