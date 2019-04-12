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
    bot.ready = True


@bot.client.on("RPL_LIST")
async def on_list(channel: str, *_, **__) -> None:
    """
    RPL_LIST handler. Joins the channel if we haven't already.

    :param channel:
    :return:
    """
    # We got some channel info, if we haven't joined it yet, join it now
    if channel not in bot.joined_channels:
        # Send JOIN
        bot.client.send("JOIN", channel=channel)

        # Wait for RPL_TOPIC
        await bot.wait_for("RPL_TOPIC")

        # Add to joined_channels set and log
        bot.joined_channels.add(channel)
        (bot.logger.info if bot.ready else bot.logger.debug)(f"Joined {channel}")


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
    if host.lower() == bot.nickname.lower() or not message.startswith(bot.command_prefix):
        return
    if target.lower() == bot.nickname.lower():
        target = host
    raw_message = message.lstrip(bot.command_prefix).lower()
    for k, v in bot.command_handlers.items():
        if raw_message.startswith(k) and (len(raw_message) <= len(k) or raw_message[len(k)] == " "):
            bot.logger.debug(f"Triggered {v} ({k})")
            result = await v(username=host, channel=target, message=message)
            if result is not None:
                if type(result) not in (tuple, list):
                    result = (result,)
                for x in result:
                    bot.client.send("PRIVMSG", target=target, message=x)
