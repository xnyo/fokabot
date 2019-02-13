import importlib
import logging

from singletons.config import Config
from singletons.bot import Bot

# TODO: uvloop
logging.basicConfig(level=logging.DEBUG if Config()["DEBUG"] else logging.INFO)
logging.info(
    """
  __      _                                   
 / _|    | |                                  
| |_ ___ | | ____ ___      _____   ___   ___  
|  _/ _ \| |/ / _` \ \ /\ / / _ \ / _ \ / _ \ 
| || (_) |   < (_| |\ V  V / (_) | (_) | (_) |
|_| \___/|_|\_\__,_| \_/\_/ \___/ \___/ \___/ 
"""
)
Bot(
    host=Config()["IRC_HOST"],
    port=Config()["IRC_PORT"],
    ssl=Config()["IRC_SSL"],
    nickname=Config()["BOT_NICKNAME"],
    password=Config()["BOT_PASSWORD"],
)
import events
for plugin in Config()["BOT_PLUGINS"]:
    importlib.import_module(f"plugins.{plugin}")
    Bot().logger.info(f"Loaded plugin plugins.{plugin}")
Bot().run()