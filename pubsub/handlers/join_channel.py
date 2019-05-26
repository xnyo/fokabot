from typing import Dict, Any

import pubsub
from singletons.bot import Bot

bind = Bot().pubsub_binding_manager


@bind.register_pubsub_handler("fokabot:join_channel")
@pubsub.schema({"channel": str})
async def handle(data: Dict[str, Any]) -> None:
    Bot().logger.debug(f"Joining {data['channel']} (pubsub)")
    Bot().client.send("JOIN", channel=data["channel"])
