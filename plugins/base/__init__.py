from itertools import zip_longest
from typing import Optional, Any, Callable, List, Dict

from schema import Or, SchemaError

from constants.privileges import Privileges
from plugins.base import utils
from plugins.base import filters
from utils.rippleapi import RippleApiResponseError, RippleApiError


class GenericBotError(Exception):
    pass


class Arg:
    forbidden_arg_names = ("sender", "recipient", "pm", "message")

    def __init__(
        self, key: Optional[str] = None, schema=None,
        default: Optional[Any] = None, rest: bool = False,
        optional: bool = False, example: Optional[str] = None
    ):
        assert key not in Arg.forbidden_arg_names, "Forbidden key name"
        self.key = key
        self.schema = schema
        self.default = default
        self.rest = rest
        self.optional = optional
        self.example = example

    def __str__(self):
        return f"{self.key}" \
            f"{f'={self.default}' if self.default is not None else ''}" \
            f"{f'({self.example})' if self.example is not None else ''}" \
            f"{'...' if self.rest else ''}"

    # @property
    # def optional(self) -> bool:
    #     return self.default is not None


class BotSyntaxError(Exception):
    def __init__(self, args, extra=None):
        self.args = args
        self.extra = extra


def arguments(*args: Arg, intersect_kwargs: bool = True) -> Callable:
    # TODO: Check optional args only at the end
    for x in args:
        if x.optional:
            x.schema = Or(x.schema, x.default)

    def decorator(f: Callable) -> Callable:
        async def wrapper(*, parts: List[str], **kwargs) -> Any:
            # parts = message.split(" ")[1:]
            validated_args = {}
            if args:
                if args[-1].rest:
                    parts = [y for y in parts[:len(args) - 1]] + ([" ".join(parts[len(args) - 1:])] if parts[len(args) - 1:] else [])
                for arg, part in zip_longest(args, parts, fillvalue=None):
                    try:
                        if arg is None:
                            # More arguments than needed (zip_longest)
                            raise ValueError()
                        v = arg.schema.validate(part)
                        if v is None:
                            raise ValueError()
                        validated_args[arg.key] = v
                    except (SchemaError, ValueError) as e:
                        if arg is not None and arg.optional:
                            validated_args[arg.key] = arg.default
                        else:
                            raise BotSyntaxError(args)
                        # print(e)
                        # raise BotSyntaxError(args)

            final_kwargs = {**validated_args, **kwargs}
            if intersect_kwargs:
                final_kwargs = utils.required_kwargs_only(f, {**validated_args, **kwargs})
            return await f(**final_kwargs)
        return wrapper
    return decorator


def private_only(f: Callable) -> Callable:
    return trigger_filter_and(filters.is_private)(f)


def public_only(f: Callable) -> Callable:
    return trigger_filter_and(filters.is_public)(f)


def errors(f: Callable) -> Callable:
    async def wrapper(
        *, command_name: str, **kwargs
    ) -> Any:
        try:
            return await f(**kwargs)
        except RippleApiResponseError as e:
            msg = e.data.get("message", None)
            if msg is None:
                return f"API Error: {e}"
            return msg
        except RippleApiError as e:
            return f"General API error: {e}"
        except GenericBotError as e:
            return str(e)
        except BotSyntaxError as e:
            first_optional = next((x for x in e.args if x.optional), None)
            if e.extra is not None:
                return e.extra
            return f"Syntax: !{command_name} {' '.join(f'<{x}>' if first_optional is None or x != first_optional else f'[{str(x)}' for x in e.args)}{']' if first_optional is not None else ''}"
    return wrapper


def base(f: Callable) -> Callable:
    return arguments(intersect_kwargs=True)(f)


def protected(required_privileges: Privileges) -> Callable:
    def decorator(f: Callable) -> Callable:
        async def wrapper(*, sender: Dict[str, Any], **kwargs) -> Any:
            if not Privileges(sender["privileges"]).has(required_privileges):
                return "You don't have the required privileges to trigger this command."
            return await f(sender=sender, **kwargs)
        return wrapper
    return decorator


def _trigger_filter(*filters_: Callable[..., bool], checker: Callable[..., bool] = None) -> Callable:
    def decorator(f: Callable) -> Callable:
        async def wrapper(**kwargs) -> Any:
            if not checker(x(**utils.required_kwargs_only(x, kwargs)) for x in filters_):
                return
            return await f(**kwargs)
        return wrapper
    return decorator


def trigger_filter_or(*filters_: Callable[..., bool]) -> Callable:
    return _trigger_filter(*filters_, checker=any)


def trigger_filter_and(*filters_: Callable[..., bool]) -> Callable:
    return _trigger_filter(*filters_, checker=all)