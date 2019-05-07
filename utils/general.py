def safefify_username(username: str) -> str:
    """
    Returns the safe username from a normal username
    (lowercase, stripped and with underscores instead of spaces)

    :param username: input username
    :return: safe username
    """
    return username.lower().strip().replace(" ", "_")
