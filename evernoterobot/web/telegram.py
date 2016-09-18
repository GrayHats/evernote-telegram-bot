import asyncio
from aiohttp import web

from bot.model import TelegramUpdateLog


async def handle_update(request):
    try:
        data = await request.json()
        request.app.logger.info(request.path_qs)
        request.app.logger.info(str(data))
        TelegramUpdateLog.create(update_data=data,
                                 headers=dict(request.headers))
        asyncio.ensure_future(request.app.bot.handle_update(data))
    except Exception as e:
        request.app.logger.fatal('Exception: {0}, Data: {1}'.format(e, data), exc_info=1)

    return web.Response(body=b'ok')
