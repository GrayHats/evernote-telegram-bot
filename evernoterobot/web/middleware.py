import settings
from web import cookies
from web.dashboard import login
from web.urls import dashboard_url

from aiohttp import web as aioweb


async def session_middleware(app, handler):
    async def middleware_handler(request):
        if request.path == dashboard_url():
            return await login(request)
        if request.cookies and request.cookies.get('dashboard'):
            data = cookies.decode(request.cookies['dashboard'])
            username = data.get('login')
            if filter(lambda x: x['login'] == username, settings.ADMINS):
                # TODO: check expire_time
                # TODO: renew expire_time
                return await handler(request)
        return aioweb.HTTPFound(settings.DASHBOARD['root_url'])
    return middleware_handler