import datetime
import secrets
import string

from collections import Sequence

ALPHABET = string.ascii_letters + string.digits


def safefify_username(username: str) -> str:
    """
    Returns the safe username from a normal username
    (lowercase, stripped and with underscores instead of spaces)

    :param username: input username
    :return: safe username
    """
    return username.lower().strip().replace(" ", "_")


def random_secure_string(length: int, alphabet: Sequence = None) -> str:
    """
    Generates a random secure string from a give alphabet.

    :param length: length of the generated string
    :param alphabet: the alphabet. Optional. Default = uppercase and lowercase letters + numbers.
    :return: the generated string
    """
    if alphabet is None:
        alphabet = ALPHABET
    return "".join(secrets.choice(alphabet) for _ in range(length))


def rfc3339_to_datetime(dt: str) -> datetime.datetime:
    """
    "Converts" a RFC3339 string to a datetime.
    Does not account for timezones.
    Used for mirislou, since all timestamps are guaranteed
    to be returned as UTC.
    Should be good enough for now.

    :param dt: Input string, must be UTC!
    :return: datetime object, WITH NO TIMEZONE CONVERSION/SUPPORT!
    """
    # TODO: https://pypi.org/project/iso8601
    return datetime.datetime.strptime(dt.split("+")[0], "%Y-%m-%dT%H:%M:%S")
