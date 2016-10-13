import settings
from web import cookies

from aiohttp import web as aioweb


async def session_middleware(app, handler):
    async def middleware_handler(request):
        if request.cookies and request.cookies.get('dashboard'):
            data = cookies.decode(request.cookies['dashboard'])
            login = data.get('login')
            if filter(lambda x: x['login'] == login, settings.ADMINS):
                # TODO: check expire_time
                # TODO: renew expire_time
                return await handler(request)
        return aioweb.HTTPFound(settings.DASHBOARD['root_url'])
    return middleware_handler