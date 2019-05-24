import asyncio

from singletons.bot import Bot

bot = Bot()


@bot.client.on("CLIENT_CONNECT")
async def on_connect(**_) -> None:
    """
    Executed when connecting. Sends PASS/NICK and requests all channels

    :param _:
    :return:
    """
    # Send first PASS, then NICK
    bot.logger.info("Logging in")
    bot.client.send("PASS", password=bot.password)
    bot.client.send("NICK", nick=bot.nickname)

    # Wait for MOTD (successfully logged in)
    await bot.wait_for("RPL_ENDOFMOTD", "ERR_NOMOTD")

    # Request channels (joined in @RPL_LIST) and wait for RPL_LISTEND
    bot.client.send("LIST")
    # TODO: Periodically send LIST to the server
    bot.reconnecting = False


@bot.client.on("RPL_LIST")
async def on_list(channel: str, *_, **__) -> None:
    """
    RPL_LIST handler. Joins the channel if we haven't already.

    :param channel:
    :return:
    """
    # We got some channel info, if we haven't joined it yet, join it now
    if channel not in bot.joined_channels:
        if not bot.ready:
            # We have just started the bot, add the clients to the login channels queue
            bot.login_channels_left.add(channel.lower())
        else:
            # Immediately join if this is a new channel
            bot.client.send("JOIN", channel=channel)


@bot.client.on("RPL_LISTEND")
async def on_list_end(*args, **kwargs) -> None:
    if bot.ready:
        # Wait for JOINs only when starting the bot
        return
    for channel in bot.login_channels_left:
        bot.client.send("JOIN", channel=channel)
    bot.logger.debug(f"Got RPL_LISTEND, started waiting for RPL_TOPIC for {len(bot.login_channels_left)} channels")
    while bot.login_channels_left:
        bot.login_channels_left.remove(await bot.login_channels_queue.get())
    bot.logger.debug("All channels joined. The bot is now ready!")
    bot.ready = True


@bot.client.on("RPL_TOPIC")
async def on_topic(channel: str, message: str):
    bot.joined_channels.add(channel)
    bot.logger.info(f"Joined {channel}")
    if not bot.ready:
        # If the bot is not ready yet, add the channels to the login channels queue
        bot.login_channels_queue.put_nowait(channel.lower())


# TODO: remove from bot.joined_channel when a channel gets disposed


@bot.client.on("PING")
def on_ping(message: str, **_) -> None:
    """
    PING handler, replies with PONG

    :param message:
    :param _:
    :return:
    """
    bot.logger.debug("Got PING from server, replying with PONG")
    bot.client.send("PONG", message=message)


@bot.client.on("PRIVMSG")
async def on_privmsg(target: str, message: str, host: str, **kwargs) -> None:
    # TODO: Add support for non-prefix commands
    is_command = message.startswith(bot.command_prefix)
    is_action = message.startswith("\x01ACTION")
    bot.logger.debug(f"{host}: {message} (cmd:{is_command}, act:{is_action})")
    if host.lower() == bot.nickname.lower() or (not is_command and not is_action):
        return
    if target.lower() == bot.nickname.lower():
        target = host
    raw_message = message[len(bot.command_prefix if is_command else "\x01ACTION"):].lower().strip()
    for k, v in (bot.command_handlers if is_command else bot.action_handlers).items():
        if raw_message.startswith(k):
            bot.logger.debug(f"Triggered {v} ({k}) [{'command' if is_command else 'action'}]")
            command_name_length = len(k.split(" "))
            result = await v(
                username=host, channel=target, message=message,
                parts=message.split(" ")[command_name_length:],
                command_name=k
            )
            if result is not None:
                if type(result) not in (tuple, list):
                    result = (result,)
                for x in result:
                    bot.client.send("PRIVMSG", target=target, message=x)


@bot.client.on("CLIENT_DISCONNECT")
async def on_disconnect(*args, **kwargs):
    """
    Called when the client is disconnected.
    Tries to reconnect to the server.

    :param kwargs:
    :return:
    """
    if bot.disposing:
        return
    if bot.reconnecting:
        bot.logger.warning("Got CLIENT_DISCONNECT, but the bot is already reconnecting.")
        return

    async def reconnect():
        """
        Performs the actual reconnection, wait for the 'ready' event and notifies '#admin'

        :return:
        """
        await bot.client.connect()
        await bot.wait_for("ready")
        # TODO: Configurable #admin
        bot.client.send("PRIVMSG", target="#admin", message="Reconnected.")

    bot.reset()
    bot.reconnecting = True
    seconds = 5     # todo: backoff?
    bot.logger.info(f"Disconnected! Starting reconnect loop in {seconds} seconds")
    await asyncio.sleep(seconds)
    while True:
        try:
            bot.logger.info(f"Trying to reconnect. Max timeout is {seconds} seconds.")
            await asyncio.wait_for(reconnect(), timeout=seconds)
            break
        except ConnectionError:
            bot.logger.warning(f"Connection failed! Retrying in {seconds} seconds")
            await asyncio.sleep(seconds)
        except asyncio.TimeoutError:
            bot.logger.warning("Server timeout")
    bot.logger.info("Reconnected!")
