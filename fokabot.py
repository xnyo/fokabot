import importlib
import logging

from utils.init_hook import InitHook
from utils.misirlouapi import MisirlouApiClient
from utils.osuapi import OsuAPIClient

try:
    import uvloop
    use_uvloop = True
except ImportError:
    use_uvloop = False

from singletons.config import Config
from singletons.bot import Bot
from utils.letsapi import LetsApiClient
from utils.rippleapi import BanchoApiClient, RippleApiClient, CheesegullApiClient


def main() -> None:
    # Logging
    logging.basicConfig(level=logging.DEBUG if Config()["DEBUG"] else logging.INFO)
    logging.info(
        """
      __      _                                   
     / _|    | |                                  
    | |_ ___ | | ____ ___      _____   ___   ___  
    |  _/ _ \\| |/ / _` \\ \\ /\\ / / _ \\ / _ \\ / _ \\ 
    | || (_) |   < (_| |\\ V  V / (_) | (_) | (_) |
    |_| \\___/|_|\\_\\__,_| \\_/\\_/ \\___/ \\___/ \\___/ 
    """
    )

    # Setup Bot singleton
    if use_uvloop:
        uvloop.install()
        logging.info("Using uvloop")
    else:
        logging.warning("Using asyncio")
    Bot(
        wss=Config()["WSS"],
        nickname=Config()["BOT_NICKNAME"],
        commands_prefix=Config()["COMMANDS_PREFIX"],
        bancho_api_client=BanchoApiClient(
            Config()["BANCHO_API_TOKEN"],
            Config()["BANCHO_API_BASE"]
        ),
        ripple_api_client=RippleApiClient(
            Config()["RIPPLE_API_TOKEN"],
            Config()["RIPPLE_API_BASE"]
        ),
        lets_api_client=LetsApiClient(
            Config()["LETS_API_BASE"]
        ),
        cheesegull_api_client=CheesegullApiClient(
            Config()["CHEESEGULL_API_BASE"]
        ),
        osu_api_client=OsuAPIClient(
            Config()["OSU_API_TOKEN"]
        ),
        misirlou_api_client=MisirlouApiClient(
            Config()["MISIRLOU_API_TOKEN"],
            Config()["MISIRLOU_API_BASE"],
        ),
        http_host=Config()["HTTP_HOST"],
        http_port=Config()["HTTP_PORT"],
        redis_host=Config()["REDIS_HOST"],
        redis_port=Config()["REDIS_PORT"],
        redis_database=Config()["REDIS_DATABASE"],
        redis_password=Config()["REDIS_PASSWORD"],
        redis_pool_size=Config()["REDIS_POOL_SIZE"],
        tinydb_path=Config()["TINYDB_PATH"],
    )
    # Register all events
    import events

    # Import all required plugins (register bot commands)
    for plugin in Config()["BOT_PLUGINS"]:
        imported_plugin = importlib.import_module(f"plugins.{plugin}")
        if hasattr(imported_plugin, "init"):
            logging.debug(f"Plugin {plugin} has init hook.")
            Bot().init_hooks.append(InitHook(plugin, getattr(imported_plugin, "init")))
        Bot().logger.info(f"Loaded plugin plugins.{plugin}")

    # Finally, run the bot
    Bot().run()


if __name__ == '__main__':
    main()
