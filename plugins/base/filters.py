from typing import Dict, Any


def is_spect(*, recipient: Dict[str, Any], pm: bool) -> bool:
    return not pm and recipient["display_name"] == "#spectator"


def is_multi(*, recipient: Dict[str, Any], pm: bool) -> bool:
    return not pm and recipient["display_name"] == "#multiplayer"


def is_private(*, pm: bool) -> bool:
    return pm


def is_public(*, pm: bool) -> bool:
    return not pm
