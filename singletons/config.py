from typing import Dict, Any

from decouple import config, Csv

from utils.singleton import singleton


@singleton
class Config:
    def __init__(self):
        token = config("RIPPLE_API_TOKEN")
        self._config: Dict[str, Any] = {
            "DEBUG": config("DEBUG", default="0", cast=bool),

            "WSS": config("WSS", default="1", cast=bool),

            "BOT_NICKNAME": config("BOT_NICKNAME", default="FokaBot"),

            "BOT_PLUGINS": config("BOT_PLUGINS", default="general,faq,alert,mod,system,pp,multiplayer", cast=Csv(str)),

            "COMMANDS_PREFIX": config("COMMANDS_PREFIX", default="!"),

            "RIPPLE_API_BASE": config("RIPPLE_API_BASE", default="https://ripple.moe"),
            "RIPPLE_API_TOKEN": token,

            "BANCHO_API_BASE": config("BANCHO_API_BASE", default="https://c.ripple.moe"),
            "BANCHO_API_TOKEN": config("BANCHO_API_TOKEN", default=token),

            "CHEESEGULL_API_BASE": config("CHEESEGULL_API_BASE", default="https://storage.ripple.moe"),

            "LETS_API_BASE": config("LETS_API_BASE", default="https://ripple.moe/letsapi"),

            "HTTP_HOST": config("HTTP_HOST", default="127.0.0.1"),
            "HTTP_PORT": config("HTTP_PORT", default=4334),
            "INTERNAL_API_SECRET": config("INTERNAL_API_SECRET"),

            "REDIS_HOST": config("REDIS_HOST", default="127.0.0.1"),
            "REDIS_PORT": config("REDIS_PORT", default="6379", cast=int),
            "REDIS_DATABASE": config("REDIS_DATABASE", default="0", cast=int),
            "REDIS_PASSWORD": config("REDIS_PASSWORD", default=None),
            "REDIS_POOL_SIZE": config("REDIS_POOL_SIZE", default="8", cast=int),
        }

    def __getitem__(self, item: str) -> Any:
        return self._config[item]
