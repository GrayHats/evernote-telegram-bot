from web.dashboard import login
from web import cookies
from settings import ADMINS
import time


def get_login(request):
    if request.cookies and request.cookies['evernoterobot']:
        data = cookies.decode(request.cookies['evernoterobot'])
        username = data.get('login')
        if filter(lambda x: x['login'] == username, ADMINS):
            if data.get('expire_time', 0) > time.time():
                return username


async def session_middleware(app, handler):
    async def middleware_handler(request):
        if handler.auth_required:
            if get_login(request):
                return await handler(request)
            return await login(request)
        else:
            return await handler(request)

    return middleware_handler
