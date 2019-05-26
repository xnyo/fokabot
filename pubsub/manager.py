from typing import Dict, Callable, Union, Iterable

import logging


class PubSubBindingManager:
    """
    PubSub handlers binding manager
    """
    def __init__(self):
        self.pubsub_channel_bindings: Dict[str, Callable] = {}

    def register_pubsub_handler(self, key: Union[str, Iterable[str]]) -> Callable:
        """
        Registers a pubsub handler, like this:
        ```
        >>> @bind.register_pubsub_handler("delta:something")
        >>> @pubsub.schema({"user_id": int})
        >>> async def handler(data: Dict[str, Any]) -> None:
        >>>     ...
        ```

        :param key: pubsub channel name or iterable with channel names
        :return:
        """
        def decorator(handler: Callable):
            def register(k):
                if k in self.pubsub_channel_bindings:
                    raise RuntimeError(f"Already registered pubsub handler ({k})")
                logging.getLogger("pubsub_manager").debug(f"Registered pubsub handler {k}")
                self.pubsub_channel_bindings[k] = handler
            if type(key) in (list, tuple):
                for kk in key:
                    register(kk)
            else:
                register(key)
            return handler
        return decorator

    def __contains__(self, item: Callable) -> bool:
        return item in self.pubsub_channel_bindings

    def __getitem__(self, item: str) -> Callable:
        return self.pubsub_channel_bindings[item]
