import sys
import logging.config
from os.path import realpath, dirname, join

import aiohttp.web
import aiohttp_jinja2
import jinja2

from web.middleware import session_middleware

sys.path.insert(0, realpath(dirname(dirname(__file__))))

import settings
from bot import EvernoteBot
from web.telegram import handle_update
from web.evernote import oauth_callback, oauth_callback_full_access
from web.urls import dashboard_urls

sys.path.insert(0, settings.PROJECT_DIR)

logging.config.dictConfig(settings.LOG_SETTINGS)

bot = EvernoteBot(settings.TELEGRAM['token'], 'evernoterobot')

app = aiohttp.web.Application(middlewares=[session_middleware])
app.logger = logging.getLogger('bot')

aiohttp_jinja2.setup(app, loader=jinja2.FileSystemLoader(join(dirname(__file__), 'html')))

secret_key = settings.SECRET['secret_key']

app.router.add_route('POST', '/%s' % settings.TELEGRAM['token'], handle_update)
app.router.add_route('GET', '/evernote/oauth', oauth_callback)
app.router.add_route('GET', '/evernote/oauth/full_access', oauth_callback_full_access)

for method, url, handler in dashboard_urls:
    app.router.add_route(method, url, handler)

app.bot = bot
