from itertools import zip_longest
from typing import Callable, Any, Tuple, Optional

from schema import SchemaError, Or


class Arg:
    def __init__(self, key: Optional[str] = None, schema=None, default: Optional[Any] = None, rest: bool = False):
        self.key = key
        self.schema = schema
        self.default = default
        self.rest = rest

    def __str__(self):
        return f"{self.key}{f'={self.default}' if self.default is not None else ''}{'...' if self.rest else ''}"

    @property
    def optional(self):
        return self.default is not None


class BotSyntaxError(Exception):
    def __init__(self, args):
        self.args = args


def arguments(*args: Tuple[Arg]) -> Callable:
    # TODO: Check optional args only at the end
    for x in args:
        if x.optional:
            x.schema = Or(x.schema, None)

    def decorator(f: Callable) -> Callable:
        async def wrapper(username: str, channel: str, message: str, *_, **__) -> Any:
            parts = message.split(" ")[1:]
            validated_args = {}
            if args[-1].rest:
                parts = [x for x in parts[:len(args) - 1]] + ([" ".join(parts[len(args) - 1:])] if parts[len(args) - 1:] else [])
            for arg, part in zip_longest(args, parts, fillvalue=None):
                try:
                    v = arg.schema.validate(part)
                    if v is None:
                        raise ValueError()
                    validated_args[arg.key] = v
                except (SchemaError, ValueError) as e:
                    if arg.optional:
                        validated_args[arg.key] = arg.default
                    else:
                        raise BotSyntaxError(args)
                    # print(e)
                    # raise BotSyntaxError(args)
            return await f(username, channel, **validated_args)
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


def errors(f: Callable) -> Callable:
    async def wrapper(username: str, channel: str, message: str, *args, **kwargs) -> Any:
        try:
            return await f(username, channel, message, *args, **kwargs)
        except BotSyntaxError as e:
            first_optional = next((x for x in e.args if x.optional), None)
            return f"Syntax: {message.split(' ')[0]} {' '.join(str(x) if first_optional is None or x != first_optional else f'[{str(x)}' for x in e.args)}{']' if first_optional is not None else ''}"
    return wrapper


def base(f: Callable) -> Callable:
    return errors(f)
