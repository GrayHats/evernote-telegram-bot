from aiohttp.web import Response

from bot.model import TelegramUpdateLog


async def handle_update(request):
    try:
        data = await request.json()
        request.app.logger.info(request.path_qs)
        request.app.logger.info(str(data))
        TelegramUpdateLog.create(update=data, headers=dict(request.headers))
        await request.app.bot.handle_update(data)
    except Exception as e:
        message = 'Exception: {0}, Data: {1}'.format(e, data)
        request.app.logger.fatal(message, exc_info=1)
    return Response(body=b'ok')
