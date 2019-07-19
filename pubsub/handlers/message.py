from typing import Dict, Any

import pubsub
from singletons.bot import Bot
from utils.schema import NonEmptyString
from ws.messages import WsChatMessage

bind = Bot().pubsub_binding_manager

@bind.register_pubsub_handler("fokabot:message")
@pubsub.schema({"recipient": NonEmptyString, "message": NonEmptyString})
async def handle(data: Dict[str, Any]) -> None:
    Bot().client.send(WsChatMessage(data["message"], data["recipient"]))
