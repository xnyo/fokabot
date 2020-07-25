from typing import Dict, Any, TypeVar, Optional, Union

from constants.events import WsEvent


class WsMessage:
    def __init__(self, type_: str, data=None):
        if data is None:
            data = {}
        self.type_ = type_
        if type(data) is dict:
            data = dict(data)
        elif callable(getattr(data, "__dict__", None)):
            # lol pycharm
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
    def __init__(self, token: str):
        super(WsAuth, self).__init__("auth", {"token": token})


class WsSubscribe(WsMessage):
    def __init__(self, event: WsEvent, data: Optional[Dict[str, Any]] = None):
        o = {"event": event.value}
        if data is not None:
            o['data'] = data
        super(WsSubscribe, self).__init__("subscribe", o)


class WsJoinChatChannel(WsMessage):
    def __init__(self, channel: str):
        super(WsJoinChatChannel, self).__init__("join_chat_channel", {"name": channel})


class WsPong(WsMessage):
    def __init__(self):
        super(WsPong, self).__init__("pong")


class WsChatMessage(WsMessage):
    def __init__(self, message: str, recipient: Union[str, int]):
        super(WsChatMessage, self).__init__("chat_message", {"message": message, "target": recipient})


class WsSubscribeMatch(WsSubscribe):
    def __init__(self, match_id: int):
        super(WsSubscribeMatch, self).__init__(WsEvent.MULTIPLAYER, {"match_id": match_id})


class WsUnsubscribeMatch(WsSubscribe):
    def __init__(self, match_id: int):
        super(WsUnsubscribeMatch, self).__init__(WsEvent.MULTIPLAYER, {"match_id": match_id})


class WsResume(WsMessage):
    def __init__(self, token: str):
        super(WsResume, self).__init__("resume", {"token": token})


class WsSuspend(WsMessage):
    def __init__(self):
        super(WsSuspend, self).__init__("suspend")
