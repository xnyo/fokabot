from itertools import zip_longest
from typing import Callable, Any, Tuple

from schema import SchemaError
from collections import namedtuple

Arg = namedtuple("Arg", ("key", "schema", "default"), defaults=(None,) * 3)


def arguments(*args: Tuple[Arg]) -> Callable:
    def decorator(f: Callable) -> Callable:
        async def wrapper(username: str, channel: str, message: str, *_, **__) -> Any:
            parts = message.split(" ")[1:]
            validated_args = {}
            for arg, part in zip_longest(args, parts, fillvalue=None):
                try:
                    v = arg.schema.validate(part)
                    if v is None:
                        if arg.optional:
                            v = arg.default
                    validated_args[arg.key] = v
                except (SchemaError, ValueError) as e:
                    if arg.default is not None:
                        validated_args[arg.key] = arg.default
                    else:
                        print(str(e))
                        return
            return await f(username, channel, validated_args)
        return wrapper
    return decorator


def _private_public_wrapper(private: bool, f: Callable) -> Callable:
    async def wrapper(username: str, channel: str, *args, **kwargs) -> Any:
        if channel.startswith("#") == private:  # 🅱️onchi insegna
            return
        return await f(username, channel, *args, **kwargs)
    return wrapper


def private_only(f: Callable) -> Callable:
    return _private_public_wrapper(True, f)


def public_only(f: Callable) -> Callable:
    return _private_public_wrapper(False, f)
