import sys
import logging.config
from os.path import realpath, dirname, join

import aiohttp.web
import aiohttp_jinja2
import jinja2

from web.dashboard import list_downloads, list_failed_updates, login, dashboard, \
    list_updates, fix_failed_update, list_users, view_telegram_update_logs

sys.path.insert(0, realpath(dirname(dirname(__file__))))

import settings
from bot import EvernoteBot
from web.telegram import handle_update
from web.evernote import oauth_callback, oauth_callback_full_access
from web.urls import dashboard_url

sys.path.insert(0, settings.PROJECT_DIR)

logging.config.dictConfig(settings.LOG_SETTINGS)

bot = EvernoteBot(settings.TELEGRAM['token'], 'evernoterobot')

app = aiohttp.web.Application()
app.logger = logging.getLogger('bot')

aiohttp_jinja2.setup(app,
    loader=jinja2.FileSystemLoader(
        join(dirname(__file__), 'html')
    )
)

secret_key = settings.SECRET['secret_key']

app.router.add_route('POST', '/%s' % settings.TELEGRAM['token'], handle_update)
app.router.add_route('GET', '/evernote/oauth', oauth_callback)
app.router.add_route('GET', '/evernote/oauth/full_access', oauth_callback_full_access)

# dashboard
app.router.add_route('GET', dashboard_url(), login)
app.router.add_route('GET', dashboard_url('/dashboard'), dashboard)
app.router.add_route('GET', dashboard_url('/downloads'), list_downloads)
app.router.add_route('GET', dashboard_url('/failed_updates'), list_failed_updates)
app.router.add_route('GET', dashboard_url('/queue'), list_updates)
app.router.add_route('GET', dashboard_url('/users'), list_users)
app.router.add_route('GET', dashboard_url('/logs'), view_telegram_update_logs)
app.router.add_route('POST', dashboard_url('/fix_failed_update'), fix_failed_update)

app.bot = bot
