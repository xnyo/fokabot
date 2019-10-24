from enum import Enum


class WsEvent(Enum):
    CHAT_CHANNELS = "chat_channels"
    MULTIPLAYER = "multiplayer"
    LOBBY = "lobby"
