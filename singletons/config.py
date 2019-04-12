from typing import Dict, Any

from decouple import config, Csv

from utils.singleton import singleton


@singleton
class Config:
    def __init__(self):
        token = config("RIPPLE_API_TOKEN")
        self._config: Dict[str, Any] = {
            "DEBUG": config("DEBUG", default="0", cast=bool),

            "IRC_HOST": config("IRC_HOST", default="irc.ripple.moe"),
            "IRC_PORT": config("IRC_PORT", default="6667", cast=int),
            "IRC_SSL": config("IRC_SSL", default="1", cast=bool),

            "BOT_NICKNAME": config("BOT_NICKNAME", default="FokaBot"),
            "BOT_PASSWORD": config("BOT_PASSWORD", default=""),

            "BOT_PLUGINS": config("BOT_PLUGINS", default="general,faq,alert,mod,system", cast=Csv(str)),

            "COMMANDS_PREFIX": config("COMMANDS_PREFIX", default="!"),

            "RIPPLE_API_BASE": config("RIPPLE_API_BASE", default="https://ripple.moe"),
            "RIPPLE_API_TOKEN": token,

            "BANCHO_API_BASE": config("BANCHO_API_BASE", default="https://c.ripple.moe"),
            "BANCHO_API_TOKEN": config("BANCHO_API_TOKEN", default=token),

            "HTTP_HOST": config("HTTP_HOST", default="127.0.0.1"),
            "HTTP_PORT": config("HTTP_PORT", default=4334),
            "INTERNAL_API_SECRET": config("INTERNAL_API_SECRET"),
        }

    def __getitem__(self, item: str) -> Any:
        return self._config[item]
