from typing import Dict, Any

from constants.events import WsEvent
from singletons.bot import Bot
from ws.client import LoginFailedError
from ws.messages import WsSubscribe, WsAuth, WsJoinChatChannel, WsPong, WsChatMessage

bot = Bot()

@bot.client.on("connected")
async def connected():
    bot.logger.debug("Ws client started, now logging in")
    try:
        bot.client.send(WsAuth(bot.nickname, bot.bancho_api_client.token))
        results = await bot.client.wait("msg:auth_success", "msg:auth_failure")
        if "auth_failure" in results:
            bot.logger.info("Login failed")
            raise LoginFailedError()
        bot.logger.info("Logged in successfully")
    except LoginFailedError:
        bot.logger.error("Login failed! Now disposing.")
        bot.loop.stop()
    else:
        bot.client.send(WsSubscribe(WsEvent.CHAT_CHANNELS))
        await bot.client.wait("msg:subscribed")
        bot.logger.debug("Subscribed to chat channel events. Now joining channels")
        channels = await bot.bancho_api_client.get_all_channels()
        bot.login_channels_left |= {x["name"].lower() for x in channels}
        for channel in channels:
            bot.logger.debug(f"Joining {channel['name']}")
            bot.client.send(WsJoinChatChannel(channel["name"]))


@bot.client.on("msg:chat_channel_joined")
async def chat_channel_joined(name: str, **kwargs):
    bot.logger.info(f"Joined {name}")
    if not bot.ready:
        bot.login_channels_left.remove(name.lower())
        if not bot.login_channels_left:
            bot.ready = True
            bot.logger.info("Bot ready!")


@bot.client.on("msg:chat_channel_added")
async def chat_channel_added(name: str, **kwargs):
    bot.logger.debug(f"Channel {name} added")
    bot.client.send(WsJoinChatChannel(name))


@bot.client.on("msg:chat_channel_removed")
async def chat_channel_removed(name: str, **kwargs):
    bot.logger.debug(f"Channel {name} removed")


@bot.client.on("msg:chat_channel_left")
async def chat_channel_removed(name: str, **kwargs):
    bot.logger.info(f"Left {name}")


@bot.client.on("msg:ping")
async def ping():
    bot.logger.debug("Got PINGed by the server. Answering.")
    bot.client.send(WsPong())


@bot.client.on("msg:chat_message")
async def on_message(sender: Dict[str, Any], recipient: str, message: str, **kwargs) -> None:
    is_command = message.startswith(bot.command_prefix)
    is_action = message.startswith("\x01ACTION")
    bot.logger.debug(f"{sender['username']}{sender['api_identifier']}: {message} (cmd:{is_command}, act:{is_action})")
    nick = sender["username"]
    if nick.lower() == bot.nickname.lower() or (not is_command and not is_action):
        return
    if recipient.lower() == bot.nickname.lower():
        recipient = nick
    raw_message = message[len(bot.command_prefix if is_command else "\x01ACTION"):].lower().strip()
    for k, v in (bot.command_handlers if is_command else bot.action_handlers).items():
        if raw_message.startswith(k):
            bot.logger.debug(f"Triggered {v} ({k}) [{'command' if is_command else 'action'}]")
            command_name_length = len(k.split(" "))
            result = await v(
                username=nick, channel=recipient, message=message,
                parts=message.split(" ")[command_name_length:],
                command_name=k
            )
            if result is not None:
                if type(result) not in (tuple, list):
                    result = (result,)
                for x in result:
                    bot.client.send(WsChatMessage(x, recipient))
