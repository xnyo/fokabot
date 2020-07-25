from itertools import zip_longest
from typing import Optional, Any, Callable, List, Dict, Iterable

from abc import ABC
from schema import Or, SchemaError

from constants.privileges import Privileges
from plugins.base import utils
from plugins.base import filters
from utils.rippleapi import RippleApiResponseError, RippleApiError


class Command(ABC):
    def __init__(self, name: Optional[str], handler: Callable):
        self.handler = handler
        self.name = name

    def __str__(self) -> str:
        return f"{self.name} {self.handler}"


class RegexCommandWrapper:
    def __init__(self, pattern, handler: Callable, pre: Optional[Callable] = None):
        self.pre = pre
        self.pattern = pattern
        self.handler = handler

    def __str__(self) -> str:
        return f"RegexCommand: {self.pattern} {self.handler}"


class CommandWrapper(Command):
    def __init__(self, *args, aliases: Optional[Iterable[str]] = None, **kwargs):
        super(CommandWrapper, self).__init__(*args, **kwargs)
        if aliases is None:
            aliases = []
        self.aliases = aliases

    def __str__(self) -> str:
        return f"Command: {super(CommandWrapper, self).__str__()}"


class CommandAlias(Command):
    def __init__(self, *args, root_name: str, **kwargs):
        super(CommandAlias, self).__init__(*args, **kwargs)
        self.root_name = root_name

    def __str__(self):
        return f"Alias: {super(CommandAlias, self).__str__()}"


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
                final_kwargs = utils.required_kwargs_only(f, **validated_args, **kwargs)
            return await f(**final_kwargs)
        return wrapper
    return decorator


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
            return f"Syntax: !{command_name} {' '.join(f'<{x}>' if first_optional is None or x != first_optional else f'[<{str(x)}>' for x in e.args)}{']' if first_optional is not None else ''}"
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


def tournament_staff_or_host(f: Callable) -> Callable:
    """
    Allows this command only if the sender is the host of this match or if the sender
    has the Privileges.USER_TOURNAMENT_STAFF privilege or if the sender is the api
    owner of the match.

    You MUST use this decorator after
    @plugins.base.multiplayer_only
    @resolve_mp

    :param f:
    :return:
    """
    import singletons.bot

    async def wrapper(*, sender: Dict[str, Any], match_id: int, **kwargs) -> Any:
        # TODO: Walrus
        can = Privileges(sender["privileges"]).has(Privileges.USER_TOURNAMENT_STAFF)
        if not can:
            match_info = await singletons.bot.Bot().bancho_api_client.get_match_info(match_id)
            can = match_info["host_api_identifier"] == sender["api_identifier"] \
                or match_info["api_owner_user_id"] == sender["user_id"]
        if not can:
            return "You must be the host of the match to trigger this command."
        return await f(sender=sender, match_id=match_id, **kwargs)
    return wrapper


def _trigger_filter(*filters_: Callable[..., bool], checker: Callable[..., bool] = None) -> Callable:
    def decorator(f: Callable) -> Callable:
        async def wrapper(**kwargs) -> Any:
            if not checker(x(**utils.required_kwargs_only(x, **kwargs)) for x in filters_):
                return
            return await f(**kwargs)
        return wrapper
    return decorator


def trigger_filter_or(*filters_: Callable[..., bool]) -> Callable:
    return _trigger_filter(*filters_, checker=any)


def trigger_filter_and(*filters_: Callable[..., bool]) -> Callable:
    return _trigger_filter(*filters_, checker=all)


def private_only(f: Callable) -> Callable:
    return trigger_filter_and(filters.is_private)(f)


def public_only(f: Callable) -> Callable:
    return trigger_filter_and(filters.is_public)(f)


def multiplayer_only(f: Callable) -> Callable:
    return trigger_filter_and(filters.is_multi)(f)


def wrap_response(dest: Callable) -> Callable:
    """
    Sends the response to the channel/user returned by the provided callable.
    The callable will receive the same arguments as the decorated function.
    Useful when working with arbitrary handlers (eg: @on('tournament_...')), which
    do not support sending messages with return by default (supported only by
    message handlers)
    """
    import singletons.bot

    def decorator(f: Callable) -> Callable:
        async def wrapper(**kwargs) -> Any:
            msg = await f(**kwargs)
            if msg is not None:
                singletons.bot.Bot().send_message(msg, dest(**kwargs))
        return wrapper
    return decorator


def wrap_response_multiplayer(f: Callable) -> Callable:
    """
    Sends the string returned by this handler to the channel of this
    tournament match. If it returns None, nothing is sent.
    The function above must be tournament-resolved
    (put this decorator after @plugins.tournament.resolve_*)
    """
    return wrap_response(lambda match, *_: f"#multi_{match.bancho_match_id}")(f)


def wrap_caller(f: Callable) -> Callable:
    async def wrapper(sender: Dict[str, Any], **kwargs) -> Any:
        msg = await f(sender=sender, **kwargs)
        if msg is not None:
            return f"{sender['username']}, {msg[0].lower() + msg[1:]}"
    return wrapper
