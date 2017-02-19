from web.admin.handlers import login
from web.admin.handlers import get_login


async def session_middleware(app, handler):
    async def middleware_handler(request):
        if hasattr(handler, 'auth_required') and handler.auth_required:
            if get_login(request):
                return await handler(request)
            return await login(request)
        else:
            return await handler(request)

    return middleware_handler


middlewares = [
    session_middleware,
]
