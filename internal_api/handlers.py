import traceback

from aiohttp import web

from plugins import pp
from singletons.bot import Bot
from singletons.config import Config


class FokaAPIError(Exception):
    def __init__(self, status: int, message: str):
        self.status = status
        self.message = message


async def send_message(request):
    resp = {}
    try:
        secret = request.headers.get("Secret", None)
        if secret is None or secret != Config()["INTERNAL_API_SECRET"]:
            raise FokaAPIError(403, "Forbidden")
        request_data = await request.json()
        if "message" not in request_data or "target" not in request_data:
            raise FokaAPIError(400, "Missing required arguments.")
        Bot().send_message(request_data["message"], request_data["target"])
        resp = {"code": 200, "message": "ok"}
    except FokaAPIError as e:
        resp = {"code": e.status, "message": e.message}
    except:
        resp = {"code": 500, "message": "Internal server error"}
        traceback.print_exc()
    finally:
        code = resp["code"] if "code" in resp else 200
        return web.json_response(resp, status=code)


async def last(request):
    resp = {}
    try:
        secret = request.headers.get("Secret", None)
        if secret is None or secret != Config()["INTERNAL_API_SECRET"]:
            raise FokaAPIError(403, "Forbidden")
        request_data = await request.json()
        if "user_id" not in request_data:
            raise FokaAPIError(400, "Missing required arguments.")
        users = await Bot().ripple_api_client.get_user(user_id=request_data["user_id"])
        if users is None or not users:
            raise FokaAPIError(404, "No such user")
        username = users[0]["username"]
        msg = await pp.last_inner(username, pm=True)
        Bot().send_message(msg, username)
        resp = {"code": 200, "message": "ok"}
    except FokaAPIError as e:
        resp = {"code": e.status, "message": e.message}
    except:
        resp = {"code": 500, "message": "Internal server error"}
        traceback.print_exc()
    finally:
        code = resp["code"] if "code" in resp else 200
        return web.json_response(resp, status=code)

