from aiohttp import web as aioweb

import settings
from web.dashboard import login, get_login


async def session_middleware(app, handler):
    async def middleware_handler(request):
        if request.path == settings.DASHBOARD['root_url']:
            return await login(request)
        if get_login(request):
            return await handler(request)
        return aioweb.HTTPFound(settings.DASHBOARD['root_url'])
    return middleware_handler
