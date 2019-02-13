from decouple import config

from utils.singleton import singleton


@singleton
class Config:
    def __init__(self):
        self._config = {
            "DEBUG": config("DEBUG", default="0", cast=bool),

            "IRC_HOST": config("IRC_HOST", default="irc.ripple.moe"),
            "IRC_PORT": config("IRC_PORT", default="6667", cast=int),
            "IRC_SSL": config("IRC_SSL", default="1", cast=bool),

            "BOT_NICKNAME": config("BOT_NICKNAME", default="FokaBot"),
            "BOT_PASSWORD": config("BOT_PASSWORD", default=""),
        }

    def __getitem__(self, item):
        return self._config[item]
