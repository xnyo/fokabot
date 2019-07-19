from typing import Dict, Any, TypeVar

from constants.events import WsEvent


class WsMessage:
    def __init__(self, type_: str, data=None):
        if data is None:
            data = {}
        self.type_ = type_
        if type(data) is dict:
            data = dict(data)
        elif callable(getattr(data, "__dict__", None)):
            data = data.__dict__()
        else:
            raise ValueError(f"Non-serializable object in ws message data: {data} (type: {type(data)})")
        self.data = data

    @classmethod
    def dict_factory(cls, ws_message_dict: Dict[str, Any]) -> "TypeVar[WsMessage]":
        type_ = ws_message_dict.get("type", None)
        data = ws_message_dict.get("data", None)
        if type_ is None or data is None:
            raise ValueError("Invalid ws message structure")
        return cls(type_=type_, data=data)

    def __dict__(self) -> Dict[str, Any]:
        return {
            "type": self.type_,
            "data": self.data
        }
    
class WsAuth(WsMessage):
    def __init__(self, username: str, token: str):
        super(WsAuth, self).__init__("auth", {"username": username, "token": token})


class WsSubscribe(WsMessage):
    def __init__(self, event: WsEvent):
        super(WsSubscribe, self).__init__("subscribe", {"event": event.value})


class WsJoinChatChannel(WsMessage):
    def __init__(self, channel: str):
        super(WsJoinChatChannel, self).__init__("join_chat_channel", {"name": channel})


class WsPong(WsMessage):
    def __init__(self):
        super(WsPong, self).__init__("pong")


class WsChatMessage(WsMessage):
    def __init__(self, message: str, recipient: str):
        super(WsChatMessage, self).__init__("chat_message", {"message": message, "target": recipient})
