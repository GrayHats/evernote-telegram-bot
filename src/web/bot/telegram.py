import asyncio
from aiohttp.web import Response

from bot.model import TelegramUpdateLog


async def handle_update(request):
    data = await request.json()
    logger = request.app.logger
    logger.info('[REQUEST] Query string: {0}, Data: {1}'.format(request.path_qs, str(data)))
    asyncio.ensure_future(request.app.bot.handle_update(data))
    try:
        TelegramUpdateLog.create(update=data, headers=dict(request.headers))
    except Exception:
        logger.fatal("Can't create update log entry", exc_info=1)
    return Response(body=b'ok')
