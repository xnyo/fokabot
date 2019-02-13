import logging

from singletons.config import Config
from singletons.bot import Bot

logging.basicConfig(level=logging.DEBUG if Config()["DEBUG"] else logging.INFO)
logging.info("FOKAWOOOOO")
Bot(
    host=Config()["IRC_HOST"],
    port=Config()["IRC_PORT"],
    ssl=Config()["IRC_SSL"],
    nickname=Config()["BOT_NICKNAME"],
    password=Config()["BOT_PASSWORD"],
)
import events
import plugins.general
Bot().run()